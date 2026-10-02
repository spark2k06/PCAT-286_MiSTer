// Directed checks for the private co-simulation adapter's memory-control model.
#include <cstdio>
#include <stdexcept>
#include <verilated.h>
#include "Vpcat_memory.h"

int main() {
    VerilatedContext context;
    Vpcat_memory memory{&context};
    const auto tick=[&]() { memory.clk=0; memory.eval(); memory.clk=1; memory.eval(); memory.clk=0; memory.eval(); };
    memory.reset=1; memory.cpu_reset=1; memory.bus_valid=0; tick();
    memory.reset=0; memory.cpu_reset=0;
    for(int i=0;i<100;++i) tick();
    const auto transfer=[&](const char *name,unsigned address,unsigned mapped,unsigned status,unsigned bhe=0) {
        memory.address=address; memory.mapped_at_address=mapped;
        memory.bus_status=status; memory.bus_valid=1; memory.bus_bhe_n=bhe;
        memory.bus_write=status==6; memory.data_oe=status==6; memory.bus_lock=0;
        memory.data_out=0x1234; memory.clk=0; memory.eval();
        unsigned waits=0;
        while(!memory.ready) {
            if(memory.protocol_error) throw std::runtime_error("Protocol fault");
            if(++waits>128) throw std::runtime_error("READY timeout");
            tick();
        }
        tick(); memory.bus_valid=0; tick();
        std::printf("MEMORY_PROBE_TRANSFER name=%s wait=%u\n",name,waits);
        return waits;
    };
    const auto require=[](bool condition,const char *message) { if(!condition) throw std::runtime_error(message); };
    const unsigned miss=transfer("reset_alias_code_miss",0xff0000,0xf0000,13);
    const unsigned hit=transfer("canonical_alias_code_hit",0xf0000,0xf0000,13);
    require(hit==2 && miss>hit,"Code miss/hit timing or alias mismatch");
    require(memory.stat_p03_misses==1 && memory.stat_p03_hits==1,"Code request duplication");
    const unsigned read_miss=transfer("data_read_miss",0x1000,0x1000,5);
    const unsigned read_hit=transfer("data_read_hit",0x1000,0x1000,5);
    require(read_hit==2 && read_miss>read_hit,"Data miss/hit timing mismatch");
    require(memory.stat_data_buffer_misses==1 && memory.stat_data_buffer_hits==1,"Data request duplication");
    transfer("upper_byte_write_update",0x1001,0x1001,6);
    require(memory.stat_data_buffer_updates==1,"Upper-byte write did not update cached word");
    transfer("data_hit_after_write",0x1000,0x1000,5);
    require(memory.stat_data_buffer_hits==2,"Write evicted cached data word");
    transfer("ram_code_miss",0x8000,0x8000,13);
    transfer("ram_code_invalidate",0x8000,0x8000,6);
    require(memory.stat_p03_invalidations==1,"Write did not invalidate cached code line");
    transfer("ram_code_refill",0x8000,0x8000,13);
    require(memory.stat_p03_misses==3,"Code invalidation/refill mismatch");
    transfer("write_without_allocation",0x9000,0x9000,6);
    transfer("read_after_nonallocating_write",0x9000,0x9000,5);
    require(memory.stat_data_buffer_misses==2,"Write incorrectly allocated data cache");
    memory.address=0x9200; memory.mapped_at_address=0x9200;
    memory.bus_status=13; memory.bus_write=0; memory.data_oe=0; memory.bus_valid=1;
    tick(); tick(); tick();
    memory.cpu_reset=1; tick(); memory.cpu_reset=0; memory.bus_valid=0;
    for(int i=0;i<100;++i) tick();
    transfer("read_after_cancelled_fill",0x9400,0x9400,13);
    require(!memory.protocol_error,"Reset cancellation raised protocol error");
    std::puts("MEMORY_PROBE_SMOKE_PASS alias hit miss update invalidate nonallocate cancel");
    return 0;
}
