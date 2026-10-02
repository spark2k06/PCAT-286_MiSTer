/* Cycle-stepped Verilator wrapper around the standalone SPK286 CPU RTL. */
#include <cstdint>

#include <verilated.h>
#include "Vspk286.h"

#include "spk286_bridge.h"

#include "spk286_memory_probe.hpp"

namespace {

VerilatedContext context;
Vspk286 top{ &context, "spk286" };
bool initialized = false;
bool stall_reported = false;
uint64_t last_event_requests = 0;
unsigned fault_reports = 0;

void
initialize_inputs()
{
    top.clk = 0;
    top.reset = 0;
    top.ready = 1;
    top.data_in = 0;
    top.execute_enable = 0;
    top.timing_policy_request = 0;
    top.intr = 0;
    top.nmi = 0;
    top.hold_request = 0;
    top.gpr_read_a_index = 0;
    top.gpr_read_b_index = 0;
    top.gpr_read_a_byte = 0;
    top.gpr_read_b_byte = 0;
    top.gpr_write_en = 0;
    top.gpr_write_byte = 0;
    top.gpr_write_index = 0;
    top.gpr_write_data = 0;
    top.ip_write_en = 0;
    top.ip_write_data = 0;
    top.flags_write_en = 0;
    top.flags_write_data = 0;
    top.flags_write_mask = 0;
    top.segment_load_en = 0;
    top.segment_load_index = 0;
    top.segment_load_selector = 0;
    top.segment_read_index = 0;
    top.segment_offset = 0;
    top.redirect = 0;
    top.fetch_request = 0;
    top.fetch_ready = 1;
}

template <typename WordArray>
uint32_t
packed_bits(const WordArray &words, unsigned bit_offset, unsigned width)
{
    const unsigned word_index = bit_offset / 32;
    const unsigned bit_index = bit_offset % 32;
    uint64_t value = words[word_index] >> bit_index;

    if ((bit_index != 0) && ((bit_index + width) > 32))
        value |= static_cast<uint64_t>(words[word_index + 1]) << (32 - bit_index);

    return static_cast<uint32_t>(value & ((uint64_t{ 1 } << width) - 1));
}

spk286_state_image_t
capture_state()
{
    spk286_state_image_t state{};

    for (unsigned i = 0; i < 8; i++) {
        const uint32_t packed = top.debug_gpr[i / 2];
        state.gpr[i] = static_cast<uint16_t>(packed >> ((i & 1) * 16));
    }

    state.ip = top.debug_ip;
    state.flags = top.debug_flags;
    state.msw_value = top.debug_protected_msw;
    state.gdtr_limit = top.debug_gdtr_limit;
    state.idtr_limit = top.debug_idtr_limit;
    state.gdtr_base = top.debug_gdtr_base;
    state.idtr_base = top.debug_idtr_base;
    state.ldtr_selector = top.debug_ldtr_selector;
    state.tr_selector = top.debug_tr_selector;
    state.ldtr_limit = top.debug_ldtr_limit;
    state.tr_limit = top.debug_tr_limit;
    state.ldtr_base = top.debug_ldtr_base;
    state.tr_base = top.debug_tr_base;
    state.instruction_ip = top.debug_instruction_ip;
    state.event_kind = top.debug_event_kind;
    state.event_vector = top.debug_event_vector;
    state.event_completed = top.event_completed;
    state.opcode = top.debug_opcode;
    state.micro_pc = top.debug_micro_pc;
    state.micro_entry = top.debug_micro_entry;
    state.micro_operation = top.debug_micro_instruction;
    state.fault_vector = top.debug_fault_vector;
    state.fault_error_code = top.debug_fault_error_code;
    state.event_error_valid = top.debug_event_error_valid;
    state.event_error_code = top.debug_event_error_code;

    const uint64_t selectors = top.debug_segment_selectors;
    const uint64_t limits = top.debug_segment_limits;
    const uint32_t access = top.debug_segment_access;

    // SPK286 packs its segment state in x86 order: ES, CS, SS, DS.
    for (unsigned i = 0; i < 4; i++) {
        state.segment_selector[i] = static_cast<uint16_t>(selectors >> (i * 16));
        state.segment_base[i] = packed_bits(top.debug_segment_bases, i * 24, 24);
        state.segment_limit[i] = static_cast<uint16_t>(limits >> (i * 16));
        state.segment_access[i] = static_cast<uint8_t>(access >> (i * 8));
    }

    return state;
}

void
sample_state()
{
    const auto state = capture_state();
    spk286_host_sync_state(&state);
}

void
report_fault_if_needed()
{
    const uint64_t requests = top.debug_timing_event_requests;
    if (requests != last_event_requests) {
        last_event_requests = requests;
        // Sample before exception delivery changes CS or switches the stack.
        // Bound output over the entire process, including CPU warm resets.
        if (top.debug_event_kind == 1 && fault_reports < 256) {
            const auto state = capture_state();
            spk286_host_report_fault(&state, ++fault_reports);
        }
    }
}

void
report_stall_if_needed()
{
    if (!stall_reported && (top.unsupported_opcode || top.shutdown ||
                            top.control_error || top.microcode_fault)) {
        stall_reported = true;
        spk286_state_image_t state{};
        for (unsigned i = 0; i < 8; i++) {
            const uint32_t packed = top.debug_gpr[i / 2];
            state.gpr[i] = static_cast<uint16_t>(packed >> ((i & 1) * 16));
        }
        state.ip = top.debug_ip;
        state.flags = top.debug_flags;
        state.msw_value = top.debug_protected_msw;
        state.gdtr_limit = top.debug_gdtr_limit;
        state.idtr_limit = top.debug_idtr_limit;
        state.gdtr_base = top.debug_gdtr_base;
        state.idtr_base = top.debug_idtr_base;
        state.ldtr_selector = top.debug_ldtr_selector;
        state.tr_selector = top.debug_tr_selector;
        state.ldtr_limit = top.debug_ldtr_limit;
        state.tr_limit = top.debug_tr_limit;
        state.ldtr_base = top.debug_ldtr_base;
        state.tr_base = top.debug_tr_base;
        state.instruction_ip = top.debug_instruction_ip;
        state.event_kind = top.debug_event_kind;
        state.event_vector = top.debug_event_vector;
        state.opcode = top.debug_opcode;
        state.micro_pc = top.debug_micro_pc;
        state.micro_entry = top.debug_micro_entry;
        state.micro_operation = top.debug_micro_instruction;
        state.fault_vector = top.debug_fault_vector;
        state.fault_error_code = top.debug_fault_error_code;
        state.event_error_valid = top.debug_event_error_valid;
        state.event_error_code = top.debug_event_error_code;
        const uint64_t selectors = top.debug_segment_selectors;
        const uint64_t limits = top.debug_segment_limits;
        const uint32_t access = top.debug_segment_access;
        for (unsigned i = 0; i < 4; i++) {
            state.segment_selector[i] = static_cast<uint16_t>(selectors >> (i * 16));
            state.segment_base[i] = packed_bits(top.debug_segment_bases, i * 24, 24);
            state.segment_limit[i] = static_cast<uint16_t>(limits >> (i * 16));
            state.segment_access[i] = static_cast<uint8_t>(access >> (i * 8));
        }
        spk286_host_report_stall(&state, top.shutdown, top.control_error,
                                 top.microcode_fault);
        if (top.shutdown)
            spk286_host_warm_reset();
    }
}

} // namespace

extern "C" void
spk286_model_reset(void)
{
    if (!initialized) {
        initialize_inputs();
        initialized = true;
    }

    top.execute_enable = 0;
    top.ready = 1;
    top.intr = 0;
    top.nmi = 0;
    memory_probe.cpu_reset();
    top.reset = 1;
    top.clk = 0;
    top.eval();
    top.clk = 1;
    top.eval();
    top.clk = 0;
    top.reset = 0;
    top.eval();
    stall_reported = false;
    last_event_requests = 0;
    sample_state();
}

extern "C" void
spk286_model_sync_state(void)
{
    if (initialized)
        sample_state();
}

extern "C" void
spk286_model_tick(void)
{
    if (!initialized)
        spk286_model_reset();

    uint8_t intr = 0;
    uint8_t nmi = 0;
    spk286_host_get_inputs(&intr, &nmi);

    top.clk = 0;
    top.reset = 0;
    top.ready = 1;
    top.execute_enable = 1;
    top.intr = intr;
    top.nmi = nmi;
    top.eval();

    memory_probe.before_tick(top);

    if (top.bus_valid && top.ready) {
        if (top.bus_status != 0xd)
            sample_state();
        top.data_in = spk286_host_bus_transfer(top.bus_status, top.address,
                                               top.bus_bhe_n, top.bus_write,
                                               top.data_out);
    } else {
        top.data_in = 0xffff;
    }
    top.eval();

    memory_probe.observe(top);
    const bool instruction_retired = top.instruction_retired;
    top.clk = 1;
    top.eval();
    memory_probe.after_tick();
    const bool event_completed = top.event_completed;
    if (!spk286_host_reset_pending()) {
        report_fault_if_needed();
        if (instruction_retired || event_completed)
            sample_state();
        report_stall_if_needed();
    }

    top.clk = 0;
    top.eval();
}
