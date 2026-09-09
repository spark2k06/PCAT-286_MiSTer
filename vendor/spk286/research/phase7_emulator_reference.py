"""Bounded original-86Box function experiment; CPU semantics, never physical proof.

86Box GPL-2.0 source is fetched into an ignored cache and extracted only into
ignored build output with its license. No emulator code enters SPK286 RTL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.request import urlopen

REVISION='3a8953d0fee171a98500ca69d5b4e9905c07272d'
FILES=('COPYING','src/cpu/cpu.c','src/cpu/386.c','src/cpu/386_ops.h',
       'src/cpu/x86_ops_rep_286_2386.h','src/cpu/x86_ops_io.h')


def differential(lines, executable, build):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from tools.run_singlestep import PreparedCase,REG_ORDER,write_batch,RESULT_RE
    from tools.singlestep import SingleStepCase
    from tools.phase7_synthetic_io import cases as out_cases
    prepared=[]
    for line in lines:
        if not line.startswith('REP '):continue
        values={key:int(value) for key,value in (item.split('=') for item in line.split()[1:])}
        if values['trap']:continue  # Original chunk/trap reference is not event-delivery emulation.
        width,df,count=values['width'],values['df'],values['initial_cx']
        regs=dict.fromkeys(REG_ORDER,0);regs.update(ax=0xF6CA,cx=count,si=0x400,di=0x500,ip=0x100,sp=0x2000,flags=0x202|(df<<10))
        ram={address:0xA5 for start in (0x3F8,0x4F8) for address in range(start,start+18)}
        for i in range(8):ram[0x400+i]=ram[0x400-i]=0x20+i
        instruction=(0xF3,0x3E,0xA3+width,0xF4)
        ram.update({0x100+i:b for i,b in enumerate(instruction)})
        expected=dict(ram)
        for i in range(count):
            for byte in range(width):expected[0x500+(-1 if df else 1)*width*i+byte]=ram[0x400+(-1 if df else 1)*width*i+byte]
        final=dict(regs,cx=values['cx'],si=values['si'],di=values['di'],ip=values['ip'])
        source=SingleStepCase(len(prepared),'SYNTHETIC 86Box differential '+line,instruction,{}, {},None,None,(),{})
        prepared.append(PreparedCase(source,tuple(regs[n] for n in REG_ORDER),tuple(final[n] for n in REG_ORDER),
                                     (0xFFFF,)*len(REG_ORDER),tuple(sorted(ram.items())),tuple(sorted(expected.items()))))
    output_lines=[line for line in lines if line.startswith('OUT ')]
    for (initial,expected,ram,transactions),line in zip(out_cases(),output_lines):
        values={key:int(value) for key,value in (item.split('=') for item in line.split()[1:])}
        assert values==dict(port=ram[1][1],width=2,data=initial[0],ip=expected[12])
        source=SingleStepCase(len(prepared),'SYNTHETIC 86Box differential '+line,(0xE7,ram[1][1],0xF4),{}, {},None,None,(),{})
        prepared.append(PreparedCase(source,initial,expected,(0xFFFF,)*len(REG_ORDER),ram,ram,expected_io=transactions))
    batch=build/'differential.bin';write_batch(batch,prepared)
    run=subprocess.run([str(executable.resolve()),'--singlestep-batch',str(batch.resolve())],capture_output=True,text=True,timeout=60)
    (build/'differential.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0 and RESULT_RE.findall(run.stdout)==[('16','16','0')],run.stdout+run.stderr
    return dict(validation='PASS',executed=16,passed=16,rep_cases=12,word_out_cases=4,
                executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                scope='Ordinary complete instruction state and data effects; nonzero event restart/priority is not a differential claim.')


def function(text,name):
    start=text.index('static int'+(' ' if '286_' in name else '\n')+name+'(')
    opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]


SUPPORT=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define UNUSED(x) x __attribute__((unused))
#define D_FLAG 0x400
typedef struct { uint32_t base; } segment;
static segment ds_segment;
static struct { uint16_t flags; uint32_t pc,oldpc; int abrt; segment *ea_seg,seg_es; } cpu_state;
static uint16_t AX,CX,SI,DI;
static int cycles,is386,is486,cpu_use_dynarec,trap,high_page,io_waitstates,nmi,nmi_enable,nmi_mask;
static uint64_t addr64,addr64_2,addr64a[2],addr64a_2[2];
static uint32_t es;
static unsigned reads_seen,writes_seen,outs_seen;
static uint16_t out_port,out_data;
static uint8_t memory[65536];
#define SEG_CHECK_READ_REP(...) ((void)0)
#define SEG_CHECK_WRITE_REP(...) ((void)0)
#define CHECK_READ_REP(...) ((void)0)
#define CHECK_WRITE_REP(...) ((void)0)
#define do_mmut_rb(...) ((void)0)
#define do_mmut_wb(...) ((void)0)
#define do_mmut_rw(...) ((void)0)
#define do_mmut_ww(...) ((void)0)
#define PREFETCH_RUN(a,b,c,d,e,f,g,h) ((void)(a),(void)(d),(void)(f))
#define CPU_BLOCK_END() ((void)0)
#define CLOCK_CYCLES(c) (cycles-=(c))
#define check_io_perm(port,width) ((void)(port),(void)(width))
static uint8_t readmemb_n(uint32_t base,uint16_t address,uint64_t translated) {
 (void)base;(void)translated;reads_seen++;return memory[address]; }
static uint16_t readmemw_n(uint32_t base,uint16_t address,uint64_t *translated) {
 (void)base;(void)translated;reads_seen++;return memory[address]|((uint16_t)memory[(uint16_t)(address+1)]<<8); }
static void writememb_n(uint32_t base,uint16_t address,uint64_t translated,uint8_t data) {
 (void)base;(void)translated;writes_seen++;memory[address]=data; }
static void writememw_n(uint32_t base,uint16_t address,uint64_t *translated,uint16_t data) {
 (void)base;(void)translated;writes_seen++;memory[address]=data;memory[(uint16_t)(address+1)]=data>>8; }
static uint8_t getbytef(void) { return memory[cpu_state.pc++]; }
static void outw(uint16_t port,uint16_t data) { outs_seen++;out_port=port;out_data=data; }
'''

MAIN=r'''
int main(void) {
 for(int width=1;width<=2;width++) for(int df=0;df<2;df++) for(int stepping=0;stepping<2;stepping++) for(int count_index=0;count_index<3;count_index++) {
  unsigned count=count_index==2?3:(unsigned)count_index;
  memset(memory,0xA5,sizeof(memory));memset(&cpu_state,0,sizeof(cpu_state));
  cpu_state.ea_seg=&ds_segment;cpu_state.pc=0x103;cpu_state.oldpc=0x100;cpu_state.flags=0x202|(df?0x400:0);
  AX=0xF6CA;CX=count;SI=0x400;DI=0x500;cycles=1000;trap=stepping;reads_seen=writes_seen=outs_seen=0;
  for(int i=0;i<8;i++) {memory[0x400+i]=(uint8_t)(0x20+i);memory[0x400-i]=(uint8_t)(0x20+i);}
  int result=width==1?opREP_MOVSB_286_a16(0):opREP_MOVSW_286_a16(0);
  unsigned elements=stepping&&count?1:count;
  assert(CX==count-elements && SI==(uint16_t)(0x400+(df?-1:1)*(int)(width*elements)) && DI==(uint16_t)(0x500+(df?-1:1)*(int)(width*elements)));
  assert(reads_seen==elements && writes_seen==elements && outs_seen==0 && AX==0xF6CA);
  assert(cpu_state.flags==(0x202|(df?0x400:0)) && cpu_state.pc==(CX?0x100:0x103) && result==(CX?1:0));
  for(unsigned i=0;i<elements;i++) for(int byte=0;byte<width;byte++) assert(memory[(uint16_t)(0x500+(df?-1:1)*(int)(width*i)+byte)]==memory[(uint16_t)(0x400+(df?-1:1)*(int)(width*i)+byte)]);
  printf("REP width=%d df=%d trap=%d initial_cx=%u cx=%u si=%u di=%u ip=%u reads=%u writes=%u\n",width,df,stepping,count,CX,SI,DI,cpu_state.pc,reads_seen,writes_seen);
 }
 for(int p=0;p<4;p++) {
  const uint8_t ports[]={0,2,3,255};cpu_state.pc=0x3849;cpu_state.flags=2;AX=0xF6CA;memory[0x3849]=ports[p];outs_seen=0;
  assert(opOUT_AX_imm(0)==0 && outs_seen==1 && out_port==ports[p] && out_data==0xF6CA && AX==0xF6CA && cpu_state.flags==2 && cpu_state.pc==0x384A);
  printf("OUT port=%u width=2 data=%u ip=%u\n",out_port,out_data,cpu_state.pc);
 }
 return 0;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path('.cache/phase7-86box-3a8953d0'))
    parser.add_argument('--build-dir',type=Path,required=True)
    parser.add_argument('--executable',type=Path)
    args=parser.parse_args();args.build_dir.mkdir(parents=True,exist_ok=False)
    records={};sources={}
    for name in FILES:
        path=args.cache/name;url=f'https://raw.githubusercontent.com/86Box/86Box/{REVISION}/{name}'
        # Pinned URL is verified afresh; reject an altered cached source.
        data=urlopen(url,timeout=60).read()
        if path.exists():assert path.read_bytes()==data,(name,'changed cached reference')
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        records[name]=dict(url=url,sha256=hashlib.sha256(data).hexdigest());sources[name]=data.decode()
    cpu=sources['src/cpu/cpu.c'];loop=sources['src/cpu/386.c'];tables=sources['src/cpu/386_ops.h']
    assert 'cpu_exec = exec386_2386;' in cpu and 'x86_setopcodes_2386(ops_2386_286, ops_2386_286_0f);' in cpu
    assert 'x86_2386_opcodes_REPE      = ops_2386_REPE_286;' in cpu
    assert '#define OP_TABLE(name) ops_2386_##name' in loop
    assert 'const OpFn OP_TABLE(286)[1024]' in tables and 'const OpFn OP_TABLE(REPE_286)[1024]' in tables
    assert 'opREP_MOVSW_286_a16' in tables and 'opOUT_AX_imm' in tables
    original=sources['src/cpu/x86_ops_rep_286_2386.h']
    selected=[function(original,'opREP_MOVSB_286_##size'),function(original,'opREP_MOVSW_286_##size')]
    macro='#define SELECTED_REP(size,CNT_REG,SRC_REG,DEST_REG) \\\n'+' \\\n'.join(re.sub(r'\\\s*\n','\n',body).rstrip() for body in selected)
    # Reconstruct only macro continuation syntax; all function statements remain original.
    expanded='\n'.join(line.rstrip(' \\')+' \\' for line in macro.splitlines())
    expanded=expanded.rstrip(' \\')+'\nSELECTED_REP(a16,CX,SI,DI)\n'
    out_function=function(sources['src/cpu/x86_ops_io.h'],'opOUT_AX_imm')
    harness=args.build_dir/'original-function-harness.c';harness.write_text(SUPPORT+expanded+out_function+MAIN)
    shutil.copyfile(args.cache/'COPYING',args.build_dir/'86Box-COPYING')
    binary=args.build_dir/'original-function-harness'
    compile_result=subprocess.run(['cc','-std=c11','-O2',str(harness),'-o',str(binary)],capture_output=True,text=True)
    (args.build_dir/'compile.log').write_text(compile_result.stdout+compile_result.stderr);compile_result.check_returncode()
    run=subprocess.run([str(binary.resolve())],capture_output=True,text=True,timeout=30)
    (args.build_dir/'reference.log').write_text(run.stdout+run.stderr);run.check_returncode()
    lines=run.stdout.splitlines();assert len(lines)==28
    report=dict(validation='PASS',reference='86Box',revision=REVISION,source_artifacts=records,
                original_function_cases=28,rep_cases=24,word_out_cases=4,physical_captures=0,
                harness_sha256=hashlib.sha256(harness.read_bytes()).hexdigest(),
                limits='Original selected 286 functions executed with simple valid-memory/logical-port services. Segment checks, translation and prefetch timing are stubs; event delivery loop is statically inspected, not executed. Trap constrains nonzero repeat chunks; this is not NMI/IRQ/TF priority evidence or a pin-level comparison.')
    if args.executable:report['differential']=differential(lines,args.executable,args.build_dir)
    (args.build_dir/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EMULATOR_FUNCTION_REFERENCE PASS: 24 REP and 4 word OUT cases; event sampling not executed; zero physical observations')


if __name__=='__main__':main()
