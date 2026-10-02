// Private, test-only wrapper for PCAT READY timing in the 86Box CPU adapter.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>
#include "Vpcat_memory.h"
extern "C" {
#include <86box/timer.h>
#include <86box/pit.h>
}

extern "C" uint8_t mem_readb_phys(uint32_t);
extern "C" uint32_t rammask;

class MemoryProbe {
    struct ShadowCache {
        const char *name;
        unsigned bits, ways, sets;
        std::vector<uint32_t> tags;
        std::vector<uint64_t> age;
        uint64_t serial=0, hits=0, misses=0, invalidations=0, updates=0;
        ShadowCache(const char *n,unsigned entries,unsigned b,unsigned w=1):
            name(n),bits(b),ways(w),sets(entries/w),tags(entries,0xffffffff),age(entries,0) {}
        void access(uint32_t address,bool write,bool code) {
            const uint32_t block=address>>bits;
            const unsigned first=(block%sets)*ways;
            unsigned hit=unsigned(tags.size()),victim=first;
            for(unsigned i=first;i<first+ways;++i) {
                if(tags[i]==block) hit=i;
                if(age[i]<age[victim]) victim=i;
            }
            if(write) {
                if(hit<tags.size()) {
                    if(code) { tags[hit]=0xffffffff; age[hit]=0; ++invalidations; }
                    else ++updates;
                }
            } else if(hit<tags.size()) { ++hits; age[hit]=++serial; }
            else { ++misses; tags[victim]=block; age[victim]=++serial; }
        }
    };
    std::array<ShadowCache,6> code_shadow{{
        {"512B_direct",64,3}, {"512B_2way",64,3,2},
        {"1KiB_direct",128,3}, {"2KiB_direct",256,3},
        {"4KiB_direct",512,3}, {"8KiB_direct",1024,3}}};
    std::array<ShadowCache,4> data_shadow{{
        {"1KiB_direct",512,1}, {"1KiB_2way",512,1,2},
        {"2KiB_direct",1024,1}, {"4KiB_direct",2048,1}}};
    VerilatedContext context;
    Vpcat_memory memory{&context, "pcat_memory"};
    bool started = false;
    bool enabled = std::getenv("PCAT_MEMORY_TIMING") &&
                   std::string(std::getenv("PCAT_MEMORY_TIMING")) == "1";
    bool at_refresh_enabled = std::getenv("PCAT_AT_REFRESH") &&
                              std::string(std::getenv("PCAT_AT_REFRESH")) == "1";
    const char *path = std::getenv("PCAT_MEMORY_PROFILE");
    uint64_t clocks = 0, retired = 0, wait = 0, queue_empty = 0;
    uint64_t routed = 0, bypassed = 0, refresh_clocks = 0;
    std::array<uint64_t,16> transfers{}, wait_status{};
    std::array<uint64_t,3> owner_requests{};
    uint16_t main_cs = 0;
    std::string phase = "boot";
    uint64_t phase_start = 0, phase_retired = 0;
    uint64_t request_start = 0;
    bool pending = false;
    std::array<uint64_t,16> latency{};
    uint64_t last_flush = 0;
    uint32_t mapped_address = 0;
    uint64_t trace_count = 0;
    FILE *trace = nullptr;

    void flush(bool final = false) {
        if (!path) return;
        const std::string temporary = std::string(path)+".tmp";
        FILE *f = std::fopen(temporary.c_str(), "w");
        if (!f) throw std::runtime_error("Cannot write memory probe profile");
        std::fprintf(f, "{\"pcat_timing\":%s,\"final\":%s,\"phase\":\"%s\","
                     "\"clocks\":%llu,\"retired\":%llu,\"wait\":%llu,\"queue_empty\":%llu,"
                     "\"routed\":%llu,\"bypassed\":%llu,\"refresh_clocks\":%llu,"
                     "\"main_cs\":%u,\"phase_clocks\":%llu,\"phase_retired\":%llu,",
                     enabled?"true":"false", final?"true":"false", phase.c_str(),
                     (unsigned long long)clocks, (unsigned long long)retired,
                     (unsigned long long)wait, (unsigned long long)queue_empty,
                     (unsigned long long)routed, (unsigned long long)bypassed,
                     (unsigned long long)refresh_clocks, main_cs,
                     (unsigned long long)(clocks-phase_start),
                     (unsigned long long)(retired-phase_retired));
        const auto array = [&](const char *name, const auto &values) {
            std::fprintf(f, "\"%s\":[", name);
            for (unsigned i=0; i<values.size(); ++i)
                std::fprintf(f, "%s%llu", i?",":"", (unsigned long long)values[i]);
            std::fprintf(f, "],");
        };
        array("transfers_by_status", transfers);
        array("wait_by_status", wait_status);
        array("latency_by_status", latency);
        array("owner_requests", owner_requests);
        std::fprintf(f, "\"code_hits\":%u,\"code_misses\":%u,\"code_fills\":%u,"
                     "\"code_invalidations\":%u,\"data_hits\":%u,\"data_misses\":%u,"
                     "\"data_fills\":%u,\"data_updates\":%u,",
                     memory.stat_p03_hits, memory.stat_p03_misses, memory.stat_p03_fills,
                     memory.stat_p03_invalidations, memory.stat_data_buffer_hits,
                     memory.stat_data_buffer_misses, memory.stat_data_buffer_fills,
                     memory.stat_data_buffer_updates);
        const auto caches=[&](const char *name,const auto &values) {
            std::fprintf(f,"\"%s\":{",name);
            for(unsigned i=0;i<values.size();++i) {
                const auto &c=values[i];
                std::fprintf(f,"%s\"%s\":{\"hits\":%llu,\"misses\":%llu,\"invalidations\":%llu,\"updates\":%llu}",
                    i?",":"",c.name,(unsigned long long)c.hits,(unsigned long long)c.misses,
                    (unsigned long long)c.invalidations,(unsigned long long)c.updates);
            }
            std::fprintf(f,"}");
        };
        std::fprintf(f,"\"posted_writes\":%u,\"posted_drains\":%u,\"posted_blocked\":%u,",
                     memory.stat_posted_count, memory.stat_drained_count, memory.stat_posted_stalls);
        std::fprintf(f,"\"at_refresh_enabled\":%s,\"at_refresh_source\":\"PIT_OUT1\","
                     "\"hold_clocks\":%u,\"hlda_clocks\":%u,\"at_refresh_count\":%u,",
                     at_refresh_enabled ? "true" : "false", memory.stat_hold_clocks,
                     memory.stat_hlda_clocks, memory.stat_at_refresh_count);
        caches("shadow_code",code_shadow); std::fprintf(f,",");
        caches("shadow_data",data_shadow); std::fprintf(f,"}\n");
        std::fclose(f);
        if (std::rename(temporary.c_str(), path))
            throw std::runtime_error("Cannot publish memory probe profile");
        last_flush = clocks;
    }

    void set_phase(const char *name) {
        flush();
        if (path) {
            FILE *f = std::fopen((std::string(path)+".phases.jsonl").c_str(), "a");
            if (!f) throw std::runtime_error("Cannot write phase receipt");
            FILE *snapshot = std::fopen(path, "r");
            int c;
            while ((c = std::fgetc(snapshot)) != EOF) std::fputc(c, f);
            std::fclose(snapshot); std::fclose(f);
        }
        phase = name; phase_start = clocks; phase_retired = retired;
        if(trace) { std::fclose(trace); trace=nullptr; }
        trace_count=0;
        if(path && (phase=="dhrystone" || phase=="whetstone")) {
            trace=std::fopen((std::string(path)+"."+phase+".csv").c_str(),"w");
            if(!trace) throw std::runtime_error("Cannot write bus trace");
            std::fprintf(trace,"clock,retired,status,address,bhe_n,cs,ip,wait\n");
        }
        flush();
    }

public:
    ~MemoryProbe() { if(trace) std::fclose(trace); if (started) flush(true); }

    void cpu_reset() {
        if (started) {
            memory.cpu_reset=1;
            memory.clk=0; memory.eval(); memory.clk=1; memory.eval();
            memory.clk=0; memory.cpu_reset=0; memory.eval();
        }
        pending=false;
    }

    template<typename CPU> void before_tick(CPU &cpu) {
        if (!started) {
            memory.reset=1; memory.cpu_reset=1; memory.bus_valid=0;
            memory.clk=0; memory.eval(); memory.clk=1; memory.eval();
            memory.clk=0; memory.reset=0; memory.cpu_reset=0; memory.eval();
            started=true;
        }
        memory.clk=0;
        memory.pit_timer1_out = pit_devs[0].data && pit_devs[0].get_outlevel ?
            pit_devs[0].get_outlevel(pit_devs[0].data,1) : 0;
        memory.cpu_hlda=cpu.hlda;
        memory.at_refresh_enable=enabled && at_refresh_enabled;
        memory.address=cpu.address;
        uint32_t mapped = cpu.address & rammask;
        if ((cpu.address >> 16) == 0xff) mapped = 0xf0000 | (cpu.address & 0xffff);
        memory.mapped_at_address=mapped;
        mapped_address=mapped;
        memory.data_out=cpu.data_out;
        memory.data_oe=cpu.data_oe;
        memory.bus_write=cpu.bus_write;
        memory.bus_bhe_n=cpu.bus_bhe_n;
        memory.bus_status=cpu.bus_status;
        memory.bus_lock=cpu.bus_lock;
        const bool mem_class=cpu.bus_status==5 || cpu.bus_status==6 || cpu.bus_status==13;
        // Scope: ordinary RAM and system BIOS. Video/option ROM, ISA, INTA,
        // DMA and device-specific AT decoding remain in 86Box.
        const bool selected=mem_class && (mapped < 0xa0000 ||
                  (mapped >= 0xf0000 && mapped < 0x100000) ||
                  (mapped >= 0x100000 && mapped < 0x260000));
        memory.bus_valid=enabled && selected && cpu.bus_valid;
        memory.eval();
        cpu.hold_request = enabled ? memory.cpu_hold : 0;
        cpu.ready = memory.bus_valid ? memory.ready :
                    enabled && memory.pending_write ? 0 : 1;
    }

    template<typename CPU> void observe(const CPU &cpu) {
        ++clocks;
        if (cpu.debug_prefetch_count == 0) ++queue_empty;
        if (cpu.instruction_retired) {
            ++retired;
            // Recognize the unchanged numeric frontend, rather than assuming
            // a DOS load segment. Detection reads RAM only, outside bus timing.
            if (!main_cs && cpu.debug_instruction_ip==0xa && cpu.debug_opcode==0x55) {
                const uint32_t base=cpu.debug_cs_base+0xa;
                const uint8_t signature[]={0x55,0x89,0xe5,0x81,0xec,0xa0,0x00,0x9a,0x0c,0x00};
                bool match=true;
                for(unsigned i=0;i<sizeof signature;++i)
                    match &= mem_readb_phys(base+i)==signature[i];
                if (match) { main_cs=cpu.debug_cs; set_phase("frontend"); }
            }
            if (main_cs && phase=="frontend" && cpu.debug_cs==uint16_t(main_cs - 0x1de + 0xec1))
                set_phase("dhrystone");
            else if (main_cs && phase=="dhrystone" && cpu.debug_cs==main_cs)
                set_phase("integer_format");
            else if (main_cs && phase=="integer_format" && cpu.debug_cs==uint16_t(main_cs - 0x1de + 0xf2e))
                set_phase("whetstone");
            else if (main_cs && phase=="whetstone" && cpu.debug_cs==main_cs)
                set_phase("math_format");
        }
        if (cpu.bus_valid) {
            const unsigned status=cpu.bus_status;
            if (!pending) { request_start=clocks; pending=true; }
            if (cpu.ready) {
                ++transfers[status]; latency[status]+=clocks-request_start;
                if(memory.bus_valid) ++routed; else ++bypassed;
                const bool codeable=(mapped_address < 0xa0000) ||
                    (mapped_address >= 0xf0000 && mapped_address < 0x260000);
                const bool ram=(mapped_address < 0xa0000) ||
                    (mapped_address >= 0x100000 && mapped_address < 0x260000);
                if(codeable && (status==13 || status==6))
                    for(auto &cache:code_shadow) cache.access(mapped_address,status==6,true);
                if(ram && (status==5 || status==6))
                    for(auto &cache:data_shadow) cache.access(mapped_address,status==6,false);
                if(trace && trace_count<250000) {
                    std::fprintf(trace,"%llu,%llu,%u,%u,%u,%u,%u,%llu\n",
                        (unsigned long long)clocks,(unsigned long long)retired,status,mapped_address,
                        cpu.bus_bhe_n,cpu.debug_cs,cpu.debug_instruction_ip,
                        (unsigned long long)(clocks-request_start));
                    if(++trace_count==250000) { std::fclose(trace); trace=nullptr; }
                }
                pending=false;
            } else { ++wait; ++wait_status[status]; }
        }
        if(memory.owner_accept) ++owner_requests[memory.owner_kind];
        if(memory.owner_refresh) ++refresh_clocks;
        if(memory.protocol_error) throw std::runtime_error("PCAT memory protocol error");
        if (clocks-last_flush>=1000000) flush();
    }

    void after_tick() {
        memory.clk=1; memory.eval();
        memory.clk=0; memory.eval();
    }
};

static MemoryProbe memory_probe;
