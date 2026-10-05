from pathlib import Path
import hashlib, json, subprocess

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
native = Path('/mnt/d/GitHub/86Box_dev')
roms = Path('/mnt/d/Desktop/86Box/roms')
disk = Path('/mnt/d/ISOs/MiSTer/286_win3.1.vhd')
program = root/'docs/evidence/p06-timing-reference-20261003/T286REF.COM'
exe = root/'build/p06-timing-reference-20261003/native6-final/86Box-native'

def identity(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': digest, 'bytes': path.stat().st_size}

prior = json.loads((root/'docs/evidence/p06-timing-reference-20261003/manifest.json').read_text())
source_files = {name: identity(native/'src'/name)
                for name in prior['local_86box_source_hashes']}
assert all(source_files[name]['sha256'] == entry['sha256']
           for name, entry in prior['local_86box_source_hashes'].items())
rom_files = {name: identity(roms/name)
             for name in prior['source_selected_rom_hashes_after_runs']}
assert all(rom_files[name]['sha256'] == entry['sha256']
           for name, entry in prior['source_selected_rom_hashes_after_runs'].items())
identities = {name:identity(path) for name,path in
              [('program',program),('native_executable',exe),('source_dos_disk',disk),
               ('original_runner',root/'SW/CPUTIME/run_native_reference.py'),
               ('private_runner',out/'run_native_reference_allprofiles.py'),
               ('validator',out/'validate_t286ref.py')]}
assert identities['program']['sha256'] == prior['native_controls']['native6-final'].get('program_sha256', '006a7be0bd962859bf929e6b0d6678c400607461ed095c9e164789acf05f2643')
assert identities['native_executable']['sha256'] == prior['native_executable_sha256']
assert identities['source_dos_disk']['sha256'] == prior['source_disk_sha256']
report = {'status':'NATIVE_PREFLIGHT_SOURCE_ROM_BINARY_PROGRAM_IDENTITIES_MATCH',
          'source_base_commit':prior['source_base_commit'],
          'current_source_head':subprocess.check_output(['git','-C',str(native),'rev-parse','HEAD'],text=True).strip(),
          'source_identity_matches_20261003_archive':True,
          'board':'[ISA] MR BIOS 286 clone', 'machine':'mr286', 'ram_kib':2048,
          'dos_config_sys':'FILES=20\r\nBUFFERS=10\r\n',
          'source_files':source_files, 'rom_files':rom_files, 'identities':identities,
          'expected_native_dispatcher':'exec386_2386',
          'expected_dispatcher_offset':0x4a75b0,
          'automatic_service_cycles':{'6000000':2,'8000000':2,'10000000':2,
                                      '12500000':3,'16000000':3,'20000000':4,'25000000':4},
          'visible_zero_config':1, 'visible_zero_service_cycles':2,
          'input_vhd_read_only':True, 'emulator_instances_owned_per_run':True}
(out/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['status'], flush=True)
