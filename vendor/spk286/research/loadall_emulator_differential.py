"""Bounded 80286 LOADALL differential experiment.

The experiment executes the original LOADALL functions from local 86Box and
PCem source trees inside a tiny, controlled C host.  The host exposes only the
memory reads, architectural state and privilege fault needed by this
instruction.  It intentionally does not import emulator code into SPK286 or
claim a physical 80286 result.

The generated C source, copied reference fragments and executable belong under
the ignored build directory.  They are not source inputs to the CPU RTL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_86BOX = Path(r"D:\GitHub\86Box_dev")
DEFAULT_PCEM = Path(r"D:\GitHub\pcem")
IMAGE_BASE = 0x800


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(repo: Path, *arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), *arguments], text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {exc}"


def extract_function(source: str) -> str:
    """Extract opLOADALL, retaining the original statements only."""
    match = re.search(r"static\s+int\s+opLOADALL\s*\(", source)
    if match is None:
        raise ValueError("opLOADALL was not found")
    opening = source.find("{", match.end())
    if opening < 0:
        raise ValueError("opLOADALL has no body")

    depth = 0
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    index = opening
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
        elif in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 1
        elif in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == "/" and next_char == "/":
                in_line_comment = True
                index += 1
            elif char == "/" and next_char == "*":
                in_block_comment = True
                index += 1
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    body = source[opening:index + 1]
                    return "static int LOADALL_REFERENCE(uint32_t fetchdat) " + body
        index += 1
    raise ValueError("unterminated opLOADALL body")


def table_classification(source: str) -> dict[str, str]:
    """Read the 286 0F table entries at indexes 04, 05 and 07."""
    marker = source.find("OP_TABLE(286_0f)")
    if marker < 0:
        raise ValueError("286_0f opcode table was not found")
    window = source[marker:marker + 2500]
    row_end = re.search(r"/\*10\*/", window)
    if row_end is None:
        raise ValueError("286_0f opcode table first row was not found")
    body = window[:row_end.start()]
    # Remove comments and split on commas; table comments contain useful row
    # labels but no entries.
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    entries = [entry.strip() for entry in body.split(",") if entry.strip()]
    # The first entry is opcode 00.  The table is 1024 entries, but only the
    # low 0F row is needed for this classification check.
    if len(entries) < 8:
        raise ValueError(f"short 286_0f table: {len(entries)} entries")
    return {f"0F {index:02X}": entries[index] for index in (4, 5, 7)}


def image_words(image_msw: int, flags: int) -> list[int]:
    words = [0] * 51
    words[3] = image_msw
    words[11] = 0x1357
    words[12] = flags
    words[13] = 0x2468
    words[14:19] = [0x1122, 0x2233, 0x3344, 0x4455, 0x5566]
    words[19:27] = [0xD1D1, 0xC1C1, 0xB1B1, 0xA1A1,
                    0x9191, 0x8181, 0x7171, 0x6161]
    words[27:39] = [0x3456, 0x9312, 0xABCD,
                    0x4567, 0x9A23, 0xBCDE,
                    0x5678, 0xF034, 0xCDEF,
                    0x6789, 0x9245, 0xEF01]
    words[39:51] = [0xBCDE, 0x000A, 0xF0F0,
                    0x2468, 0x8220, 0x1111,
                    0x1357, 0x0001, 0x2222,
                    0x369C, 0x8902, 0x3333]
    return words


def logical_read_trace() -> list[dict[str, int | str]]:
    trace: list[dict[str, int | str]] = []

    def word(address: int) -> None:
        trace.append({"kind": "W", "address": address})

    def byte(address: int) -> None:
        trace.append({"kind": "B", "address": address})

    for address in (0x806, 0x818, 0x816, 0x81A, 0x81C, 0x81E,
                    0x820, 0x822, 0x824, 0x826, 0x828, 0x82A,
                    0x82C, 0x82E, 0x830, 0x832, 0x834):
        word(address)
    trace = []
    word(0x806)
    word(0x818)
    word(0x816)
    word(0x81A)
    word(0x81C)
    word(0x81E)
    word(0x820)
    word(0x822)
    word(0x824)
    for address in (0x826, 0x828, 0x82A, 0x82C, 0x82E, 0x830, 0x832, 0x834):
        word(address)
    word(0x836)
    byte(0x838)
    byte(0x839)
    word(0x83A)
    word(0x83C)
    byte(0x83E)
    byte(0x83F)
    word(0x840)
    word(0x842)
    byte(0x844)
    byte(0x845)
    word(0x846)
    word(0x848)
    byte(0x84A)
    byte(0x84B)
    word(0x84C)
    word(0x84E)
    byte(0x850)
    word(0x852)
    word(0x854)
    byte(0x856)
    byte(0x857)
    word(0x858)
    word(0x85A)
    byte(0x85C)
    word(0x85E)
    word(0x860)
    byte(0x862)
    byte(0x863)
    word(0x864)
    return trace


def reference_state(image: list[int], initial_msw: int) -> dict[str, object]:
    def base(low: int, high_access: int) -> int:
        return low | ((high_access & 0xFF) << 16)

    return {
        "msw": (initial_msw & 1) | image[3],
        "flags": (image[12] & 0xFFD5) | 2,
        "pc": image[13],
        "gpr": image[26:18:-1],  # AX, CX, DX, BX, SP, BP, SI, DI
        "selectors": [image[18], image[17], image[16], image[15]],
        "bases": [base(image[27], image[28]), base(image[30], image[31]),
                  base(image[33], image[34]), base(image[36], image[37])],
        "limits": [image[29], image[32], image[35], image[38]],
        "access": [(image[28] >> 8) & 0xFF, (image[31] >> 8) & 0xFF,
                   (image[34] >> 8) & 0xFF, (image[37] >> 8) & 0xFF],
        "gdtr_base": base(image[39], image[40]), "gdtr_limit": image[41],
        "ldtr_selector": image[14], "ldtr_base": base(image[42], image[43]),
        "ldtr_limit": image[44], "ldtr_access": (image[43] >> 8) & 0xFF,
        "idtr_base": base(image[45], image[46]), "idtr_limit": image[47],
        "tr_selector": image[11], "tr_base": base(image[48], image[49]),
        "tr_limit": image[50], "tr_access": (image[49] >> 8) & 0xFF,
    }


def spk286_contract(case: dict[str, int], image: list[int]) -> dict[str, object]:
    if case["protected"] and case["cpl"] != 0:
        return {"outcome": "fault", "reads": [], "state": {}}
    if case["protected"] and not (image[3] & 1):
        return {"outcome": "fault", "reads": list(range(4)), "state": {}}
    state = reference_state(image, case["initial_msw"])
    state["msw"] = image[3]
    state["flags"] = image[12]
    return {"outcome": "success", "reads": list(range(51)), "state": state}


CASES = {
    "real": {"protected": 0, "cpl": 0, "initial_msw": 0, "image_msw": 0,
              "flags": 0x0202},
    "flags_reserved": {"protected": 0, "cpl": 0, "initial_msw": 0,
                        "image_msw": 0, "flags": 0xFFFF},
    "protected_cpl0": {"protected": 1, "cpl": 0, "initial_msw": 1,
                        "image_msw": 1, "flags": 0x0202},
    "protected_cpl1": {"protected": 1, "cpl": 1, "initial_msw": 1,
                        "image_msw": 1, "flags": 0x0202},
    "protected_clear_pe": {"protected": 1, "cpl": 0, "initial_msw": 1,
                            "image_msw": 0, "flags": 0x0202},
}


C_SUPPORT = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define UNUSED(x) x
#define CPU_STATUS_NOTFLATSS 0x01
#define CPU_STATUS_NOTFLATDS 0x02
#define CPU_BLOCK_END() ((void)0)
#define PREFETCH_RUN(a,b,c,d,e,f,g,h) ((void)(a),(void)(b),(void)(c),(void)(d),(void)(e),(void)(f),(void)(g),(void)(h))
#define CLOCK_CYCLES(c) (cycles -= (c))

typedef struct {
    uint16_t seg;
    uint32_t base;
    uint16_t limit;
    uint8_t access;
    uint32_t limit_low;
    uint32_t limit_high;
} x86seg;

static struct {
    uint16_t flags;
    uint16_t pc;
    uint32_t oldpc;
    x86seg seg_es, seg_cs, seg_ss, seg_ds;
} cpu_state;
static x86seg tr, ldt;
static struct { uint32_t base; uint16_t limit; } gdt, idt;
static uint16_t AX, CX, DX, BX, SP, BP, SI, DI;
static uint16_t DS, SS, CS, ES;
static uint32_t ds, ss, cs, es;
static uint16_t msw, cr0;
static int CPL;
static int cpu_cur_status;
static int cycles;
static int fault_count;
static uint16_t fault_error;
static uint8_t memory[0x1000];
static struct { char kind; uint32_t address; } reads[128];
static unsigned reads_seen;

static void x86gpf(void *unused, int error) {
    (void)unused;
    fault_count++;
    fault_error = (uint16_t)error;
}
static void flags_extract(void) { }
static uint16_t readmemw(int unused, uint32_t address) {
    (void)unused;
    reads[reads_seen].kind = 'W'; reads[reads_seen].address = address; reads_seen++;
    return (uint16_t)(memory[address] | ((uint16_t)memory[address + 1] << 8));
}
static uint8_t readmemb(int unused, uint32_t address) {
    (void)unused;
    reads[reads_seen].kind = 'B'; reads[reads_seen].address = address; reads_seen++;
    return memory[address];
}
static void put_word(uint32_t address, uint16_t value) {
    memory[address] = (uint8_t)value;
    memory[address + 1] = (uint8_t)(value >> 8);
}
static void print_words(const uint16_t *values, unsigned count) {
    putchar('[');
    for (unsigned i = 0; i < count; ++i) printf("%s%u", i ? "," : "", values[i]);
    putchar(']');
}
static void print_u32(const uint32_t *values, unsigned count) {
    putchar('[');
    for (unsigned i = 0; i < count; ++i) printf("%s%u", i ? "," : "", values[i]);
    putchar(']');
}
static void print_bytes(const uint8_t *values, unsigned count) {
    putchar('[');
    for (unsigned i = 0; i < count; ++i) printf("%s%u", i ? "," : "", values[i]);
    putchar(']');
}
static void print_observation(const char *impl, const char *case_name, int result) {
    uint16_t gpr[] = {AX, CX, DX, BX, SP, BP, SI, DI};
    uint16_t selectors[] = {ES, CS, SS, DS};
    uint32_t bases[] = {es, cs, ss, ds};
    uint16_t limits[] = {cpu_state.seg_es.limit, cpu_state.seg_cs.limit,
                         cpu_state.seg_ss.limit, cpu_state.seg_ds.limit};
    uint8_t access[] = {cpu_state.seg_es.access, cpu_state.seg_cs.access,
                        cpu_state.seg_ss.access, cpu_state.seg_ds.access};
    printf("{\"impl\":\"%s\",\"case\":\"%s\",\"result\":%d,\"fault\":%d,\"error\":%u,\"reads\":[",
           impl, case_name, result, fault_count != 0, fault_error);
    for (unsigned i = 0; i < reads_seen; ++i)
        printf("%s{\"kind\":\"%c\",\"address\":%u}", i ? "," : "", reads[i].kind, reads[i].address);
    printf("],\"state\":{\"msw\":%u,\"flags\":%u,\"pc\":%u,\"gpr\":",
           msw, cpu_state.flags, cpu_state.pc);
    print_words(gpr, 8);
    printf(",\"selectors\":"); print_words(selectors, 4);
    printf(",\"bases\":"); print_u32(bases, 4);
    printf(",\"limits\":"); print_words(limits, 4);
    printf(",\"access\":"); print_bytes(access, 4);
    printf(",\"gdtr_base\":%u,\"gdtr_limit\":%u,\"ldtr_selector\":%u,\"ldtr_base\":%u,\"ldtr_limit\":%u,\"ldtr_access\":%u,\"idtr_base\":%u,\"idtr_limit\":%u,\"tr_selector\":%u,\"tr_base\":%u,\"tr_limit\":%u,\"tr_access\":%u}}\n",
           gdt.base, gdt.limit, ldt.seg, ldt.base, ldt.limit, ldt.access,
           idt.base, idt.limit, tr.seg, tr.base, tr.limit, tr.access);
}
static void reset_case(int protected_mode, int cpl, int image_msw, uint16_t flags) {
    uint16_t image[51];
    memset(memory, 0xA5, sizeof(memory));
    memset(&cpu_state, 0, sizeof(cpu_state));
    memset(&tr, 0, sizeof(tr)); memset(&ldt, 0, sizeof(ldt));
    memset(&gdt, 0, sizeof(gdt)); memset(&idt, 0, sizeof(idt));
    AX=0xAAAA; CX=0xCCCC; DX=0xDDDD; BX=0xBBBB;
    SP=0x5555; BP=0xBBBB; SI=0x6666; DI=0x7777;
    DS=0x8888; SS=0x9999; CS=0xAAAA; ES=0xEEEE;
    ds=0x010101; ss=0x020202; cs=0x030303; es=0x040404;
    cpu_state.flags=0x1357; cpu_state.pc=0x2468; cpu_state.oldpc=0x1111;
    msw=(uint16_t)(protected_mode ? 1 : 0); cr0=(uint16_t)(protected_mode ? 1 : 0);
    CPL=cpl; cpu_cur_status=0; cycles=1000; fault_count=0; fault_error=0; reads_seen=0;
    memset(image, 0, sizeof(image));
    image[3]=(uint16_t)image_msw; image[11]=0x1357; image[12]=flags; image[13]=0x2468;
    image[14]=0x1122; image[15]=0x2233; image[16]=0x3344; image[17]=0x4455; image[18]=0x5566;
    image[19]=0xD1D1; image[20]=0xC1C1; image[21]=0xB1B1; image[22]=0xA1A1;
    image[23]=0x9191; image[24]=0x8181; image[25]=0x7171; image[26]=0x6161;
    image[27]=0x3456; image[28]=0x9312; image[29]=0xABCD;
    image[30]=0x4567; image[31]=0x9A23; image[32]=0xBCDE;
    image[33]=0x5678; image[34]=0xF034; image[35]=0xCDEF;
    image[36]=0x6789; image[37]=0x9245; image[38]=0xEF01;
    image[39]=0xBCDE; image[40]=0x000A; image[41]=0xF0F0;
    image[42]=0x2468; image[43]=0x8220; image[44]=0x1111;
    image[45]=0x1357; image[46]=0x0001; image[47]=0x2222;
    image[48]=0x369C; image[49]=0x8902; image[50]=0x3333;
    for (unsigned i = 0; i < 51; ++i) put_word(0x800 + i * 2, image[i]);
}
typedef int (*loadall_fn)(uint32_t);
static void run_case(const char *impl, const char *case_name, loadall_fn fn,
                     int protected_mode, int cpl, int image_msw, uint16_t flags) {
    reset_case(protected_mode, cpl, image_msw, flags);
    print_observation(impl, case_name, fn(0));
}
'''


def build_harness(build: Path, source_86box: str, source_pcem: str) -> tuple[Path, Path]:
    body_86box = extract_function(source_86box).replace(
        "static int LOADALL_REFERENCE", "static int LOADALL_86BOX", 1)
    body_pcem = extract_function(source_pcem).replace(
        "static int LOADALL_REFERENCE", "static int LOADALL_PCEM", 1)
    main = r'''
int main(void) {
    run_case("86Box", "real", LOADALL_86BOX, 0, 0, 0, 0x0202);
    run_case("86Box", "flags_reserved", LOADALL_86BOX, 0, 0, 0, 0xFFFF);
    run_case("86Box", "protected_cpl0", LOADALL_86BOX, 1, 0, 1, 0x0202);
    run_case("86Box", "protected_cpl1", LOADALL_86BOX, 1, 1, 1, 0x0202);
    run_case("86Box", "protected_clear_pe", LOADALL_86BOX, 1, 0, 0, 0x0202);
    run_case("PCem", "real", LOADALL_PCEM, 0, 0, 0, 0x0202);
    run_case("PCem", "flags_reserved", LOADALL_PCEM, 0, 0, 0, 0xFFFF);
    run_case("PCem", "protected_cpl0", LOADALL_PCEM, 1, 0, 1, 0x0202);
    run_case("PCem", "protected_cpl1", LOADALL_PCEM, 1, 1, 1, 0x0202);
    run_case("PCem", "protected_clear_pe", LOADALL_PCEM, 1, 0, 0, 0x0202);
    return 0;
}
'''
    harness = build / "loadall_emulator_harness.c"
    harness.write_text(C_SUPPORT + body_86box + body_pcem + main, encoding="utf-8")
    binary = build / "loadall_emulator_harness"
    return harness, binary


def expected_reference(case_name: str) -> dict[str, object]:
    case = CASES[case_name]
    image = image_words(case["image_msw"], case["flags"])
    if case["protected"] and case["cpl"] != 0:
        return {"outcome": "fault", "reads": [], "state": {}}
    state = reference_state(image, case["initial_msw"])
    return {"outcome": "success", "reads": logical_read_trace(), "state": state}


def compare_state(actual: dict[str, object], expected: dict[str, object]) -> list[str]:
    mismatches = []
    for key, value in expected.items():
        if actual.get(key) != value:
            mismatches.append(f"{key}: actual={actual.get(key)!r} expected={value!r}")
    return mismatches


def run(args: argparse.Namespace) -> dict[str, object]:
    source_86box_path = args.source_86box / "src/cpu/x86_ops_misc.h"
    source_pcem_path = args.source_pcem / "includes/private/cpu/x86_ops_misc.h"
    table_86box_path = args.source_86box / "src/cpu/386_ops.h"
    table_pcem_path = args.source_pcem / "includes/private/cpu/386_ops.h"
    source_86box = source_86box_path.read_text(encoding="utf-8")
    source_pcem = source_pcem_path.read_text(encoding="utf-8")
    table_86box = table_86box_path.read_text(encoding="utf-8")
    table_pcem = table_pcem_path.read_text(encoding="utf-8")

    build = args.build_dir.resolve()
    if build.exists() and any(build.iterdir()):
        raise SystemExit(f"refusing non-empty build directory: {build}")
    build.mkdir(parents=True, exist_ok=True)
    harness, binary = build_harness(build, source_86box, source_pcem)

    compiler = shlex.split(args.cc)
    compile_result = subprocess.run(
        compiler + ["-std=c11", "-O2", "-Wall", "-Wextra", str(harness), "-o", str(binary)],
        capture_output=True, text=True,
    )
    (build / "compile.log").write_text(compile_result.stdout + compile_result.stderr,
                                         encoding="utf-8")
    compile_result.check_returncode()
    execution = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    (build / "reference.log").write_text(execution.stdout + execution.stderr, encoding="utf-8")
    execution.check_returncode()
    observations = [json.loads(line) for line in execution.stdout.splitlines() if line.strip()]
    if len(observations) != len(CASES) * 2:
        raise RuntimeError(f"expected {len(CASES) * 2} observations, got {len(observations)}")

    grouped: dict[tuple[str, str], dict[str, object]] = {
        (item["impl"], item["case"]): item for item in observations
    }
    harness_checks = []
    for impl in ("86Box", "PCem"):
        for case_name in CASES:
            actual = grouped[(impl, case_name)]
            expected = expected_reference(case_name)
            expected_outcome = expected["outcome"]
            actual_outcome = "fault" if actual["fault"] else "success"
            mismatches = []
            if actual_outcome != expected_outcome:
                mismatches.append(f"outcome: actual={actual_outcome} expected={expected_outcome}")
            if expected_outcome == "success":
                mismatches += compare_state(actual["state"], expected["state"])
                if actual["reads"] != expected["reads"]:
                    mismatches.append("logical read trace differs")
            elif actual["reads"]:
                mismatches.append("fault path performed memory reads")
            harness_checks.append({"impl": impl, "case": case_name,
                                   "result": "PASS" if not mismatches else "FAIL",
                                   "mismatches": mismatches})

    pairwise = []
    for case_name in CASES:
        left = grouped[("86Box", case_name)]
        right = grouped[("PCem", case_name)]
        differences = [key for key in ("result", "fault", "error", "reads", "state")
                       if left[key] != right[key]]
        pairwise.append({"case": case_name,
                         "result": "AGREE" if not differences else "DISAGREE",
                         "different_fields": differences})

    differentials = []
    for case_name, case in CASES.items():
        actual = grouped[("86Box", case_name)]["state"]
        reference = reference_state(image_words(case["image_msw"], case["flags"]), case["initial_msw"])
        spk = spk286_contract(case, image_words(case["image_msw"], case["flags"]))
        if case["protected"] and case["cpl"] != 0:
            reference_delta = "same fault-before-read outcome"
        elif spk["outcome"] == "fault":
            reference_delta = "86Box/PCem success versus current SPK286 pre-commit fault"
        else:
            differences = [key for key in ("msw", "flags", "pc", "gpr", "selectors",
                                           "bases", "limits", "access", "gdtr_base",
                                           "gdtr_limit", "ldtr_selector", "ldtr_base",
                                           "ldtr_limit", "ldtr_access", "idtr_base",
                                           "idtr_limit", "tr_selector", "tr_base",
                                           "tr_limit", "tr_access")
                           if actual[key] != spk["state"][key]]
            reference_delta = "same normalized architectural state" if not differences \
                else "SPK286 current contract differs in: " + ", ".join(differences)
        differentials.append({"case": case_name, "result": reference_delta,
                              "spk286_contract": spk,
                              "86box_vs_reference_model": "PASS" if case["protected"] and case["cpl"] != 0
                              else ("PASS" if not compare_state(actual, reference) else "FAIL")})

    report = {
        "validation": "PASS_WITH_RECORDED_DIFFERENCES",
        "scope": "Controlled execution of original 86Box and PCem opLOADALL functions; no full-machine timing or silicon claim",
        "classification": {
            "86Box": table_classification(table_86box),
            "PCem": table_classification(table_pcem),
        },
        "sources": {
            "86Box": {"repo": str(args.source_86box), "commit": git_value(args.source_86box, "rev-parse", "HEAD"),
                      "status": git_value(args.source_86box, "status", "--short"),
                      "function_sha256": sha256(source_86box_path), "table_sha256": sha256(table_86box_path)},
            "PCem": {"repo": str(args.source_pcem), "commit": git_value(args.source_pcem, "rev-parse", "HEAD"),
                     "status": git_value(args.source_pcem, "status", "--short"),
                     "function_sha256": sha256(source_pcem_path), "table_sha256": sha256(table_pcem_path)},
        },
        "harness_sha256": sha256(harness),
        "pairwise": pairwise,
        "harness_checks": harness_checks,
        "differentials": differentials,
        "limitations": [
            "The host stubs prefetch, descriptor validation, event delivery and cycle timing.",
            "A 286 logical read trace is compared; SPK286's 51 word bus transactions are a separate normalized layer.",
            "The source functions are emulator evidence, not Intel architectural authority or direct hardware evidence.",
        ],
    }
    (build / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"LOADALL_EMULATOR_DIFFERENTIAL {report['validation']}")
    for item in pairwise:
        print(f"{item['case']}: {item['result']}")
    for item in differentials:
        print(f"SPK286 {item['case']}: {item['result']}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-86box", type=Path, default=DEFAULT_86BOX)
    parser.add_argument("--source-pcem", type=Path, default=DEFAULT_PCEM)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--cc", default=shutil.which("cc") or "cc",
                        help="C compiler command; use 'cc' under WSL when Windows has no compiler")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
