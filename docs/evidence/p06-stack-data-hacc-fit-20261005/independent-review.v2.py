#!/usr/bin/env python3
"""Independently read back the final sealed fit packet; launch no tools/tests."""
import ast
import collections
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
PACKET = ROOT / 'docs/evidence/p06-stack-data-hacc-fit-20261005'
PARENT = ROOT / 'docs/evidence/p06-null-segment-fit-20261005'
CORNERS = {'7_slow_1100mv_100c', '7_slow_1100mv_-40c',
           'MIN_fast_1100mv_100c', 'MIN_fast_1100mv_-40c'}
PINS = {
    'vendor/spk286/rtl/spk286_micro_executor.sv':
        ('325f51e6a91ae9c309786c17da8c22aa3264b3084314008b43b7cc41fd44f6db',
         '8d41e0187bef3081728780e4683c9e312b1f4beb1f3c40a6244d465c32799710'),
    'vendor/spk286/rtl/timed/spk286_profiled_micro_executor.sv':
        ('19882c7b14c1dd8dde73ff97ead3e47a66ba394ef474713085b468d1ad735af4',
         '2b5ca85c5939dcce3984439f8d5d9c67d590f70ad99faaa08cf139d65a33a123'),
    'sys/ascal.vhd':
        ('412aa4c447e9b6389600dabb0072ffdc5bffdd14a310962e2dc5ebff01be5186',
         '8a8382913f007cf7405aad235d6df9558ec14fc493251e31783ddb00031fd687'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(ok, note):
    if not ok:
        raise ValueError(note)


def load_file(path):
    return json.loads(path.read_bytes())


def minimum(summary, kind, group='global'):
    return min((data[kind][group]['tool_worst_slack_ns'], corner)
               for corner, data in summary['corners'].items())


def read_packet(folder):
    manifest = load_file(folder / 'manifest.json')
    archive = folder / manifest['archive']
    check(sha(archive.read_bytes()) == manifest['sha256'], 'Archive identity mismatch: ' + str(folder))
    with tarfile.open(archive) as target:
        members = target.getmembers()
        names = [member.name for member in members]
        check(len(names) == len(set(names)) == manifest['members'], 'Duplicate/count mismatch')
        check(set(names) == set(manifest['members_sha256']), 'Archive membership mismatch')
        data = {}
        for member in members:
            check(member.isfile(), 'Non-file archive member')
            raw = target.extractfile(member).read()
            expected = manifest['members_sha256'][member.name]
            check(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'], 'Archive byte mismatch: ' + member.name)
            data[member.name] = raw
    return manifest, data


class ActualReportText:
    """Read-only parser adapter around unchanged archived report text."""
    def __init__(self, raw):
        self.raw = raw

    def read_text(self, **kwargs):
        return self.raw.decode('utf-8', errors='replace')


def main():
    output = OWN / 'review.json'
    check(not output.exists(), 'Independent review must be fresh')
    manifest, data = read_packet(PACKET)
    pm, old = read_packet(PARENT)
    check(pm['sha256'] == '54cfeec050d88fad8f061ffac8ebe35c06f9e6788cd4b84b9a3dd04d0ed9f1e5', 'Parent archive changed')
    load = lambda name: json.loads(data[name])
    result, fitted, summary, original = (load(name) for name in
        ('result.json', 'fit/manifest.json', 'fit/summary.json', 'original-sdc/summary.json'))
    before, after, ledger, om = (load(name) for name in
        ('input-bindings.before.json', 'input-bindings.after.json', 'fit/vendor-ledger.json', 'original-sdc/manifest.json'))
    sources = {name.removeprefix('effective-source/'): sha(raw) for name, raw in data.items()
               if name.startswith('effective-source/')}
    parent_sources = {name.removeprefix('effective-source/'): sha(raw) for name, raw in old.items()
                      if name.startswith('effective-source/')}
    check(len(sources) == 2073 and len(parent_sources) == 2062, 'Wrong source population')
    check(sources == after['sources_sha256'] and before['sources_sha256'] == fitted['source_sha256'], 'Source receipts differ')
    check(set(sources) == set(fitted['source_sha256']), 'Frozen/effective membership differs')
    changed = {name for name in sources if sources[name] != fitted['source_sha256'][name]}
    check(changed == {'build_id.v'} and after['controlled_build_date'] ==
          {'snapshot': fitted['source_sha256']['build_id.v'], 'compiled': sources['build_id.v']}, 'Uncontrolled preflow delta')
    check(fitted['head'] == '8273c48337166188560cfae51e6efbea40dd894c', 'Wrong frozen HEAD')
    check(collections.Counter(before['input_sha256'].values()) == collections.Counter(after['input_sha256'].values()), 'Proof/input drift')
    check(before['status'] == after['status'] == 'NEXT_FIT_SOURCE_PROOF_BINDINGS_PASS', 'Source proof not accepted')
    for name in ('source-binder.py', 'source-binder.before.py'):
        check(sha(data[name]) == '89f0e3d2cd9cce43802228b75b59837edf91c98085b99db748f33fba75d310cc', 'Wrong frozen binder')
    check(sha(data['collector.py']) == '594312f134ea80c92fc6e7f7819923e868081cc8dd9627faf8d9cd7d9b41c8e1', 'Wrong collector')
    check(ledger['upstream_head'] == '8862139dfb4227c86d7906a603fcfaa44c78eb08' and
          len(ledger['imported']) == 1249, 'Canonical frozen mirror differs')
    for group in ('imported', 'downstream_overlay', 'retained_vendor_only'):
        for name, entry in ledger[group].items():
            check(sources['vendor/spk286/' + name] == entry['sha256'], 'Canonical byte mismatch: ' + name)
    check(after['vendor_ledger_sha256'] == sha(data['fit/vendor-ledger.json']), 'Frozen ledger SHA mismatch')
    for name, (reference, candidate) in PINS.items():
        check(parent_sources[name] == reference and sources[name] == candidate, 'Exact HDL transition differs: ' + name)
    hardware_suffixes = ('.sv', '.v', '.vhd', '.vh', '.mif', '.mem', '.hex', '.sdc', '.qsf', '.qip', '.qpf', '.tcl')
    common_changed_hardware = {name for name in parent_sources if name.endswith(hardware_suffixes) and
                               name != 'build_id.v' and sources[name] != parent_sources[name]}
    check(common_changed_hardware == set(PINS), 'Undeclared compiled hardware/settings change')
    check(not any(name.endswith(hardware_suffixes) for name in set(sources) - set(parent_sources)), 'Additional hardware/settings file')
    check(data['effective-source/SYSTEM.sdc'] == old['effective-source/SYSTEM.sdc'] and
          data['effective-source/config.tcl'] == old['effective-source/config.tcl'], 'SDC/features changed')
    check(summary['snapshot_manifest_sha256'] == sha(data['fit/manifest.json']) and
          original['snapshot_manifest_sha256'] == sha(data['original-sdc/manifest.json']), 'STA manifest identity differs')
    check(om['source_sha256'] == fitted['source_sha256'] and om['head'] == fitted['head'] and
          om['parent_fit'] == Path(result['candidate']).name, 'Original-SDC source ancestry differs')
    check(summary['container_image'] == original['container_image'] ==
          'sha256:1fba8b9347973365e9f7851d73f7cb035e38fefb827cbf0ed2ea291b48bdf6dd', 'Fitted/STA image differs')
    check(summary['system_sdc_overlay_sha256'] is None and original['system_sdc_overlay_sha256'] ==
          sha(data['original-sdc/overlay/SYSTEM.sdc']), 'STA overlay differs')
    check(data['original-sdc/overlay/SYSTEM.sdc'] == old['original-sdc/overlay/SYSTEM.sdc'], 'Original constraint baseline changed')
    parser = ast.parse(data['effective-source/scripts/summarize_at_50mhz_timing.py'])
    parser.body = [node for node in parser.body if isinstance(node, ast.FunctionDef) and
                   node.name in ('table_rows', 'parse_report')]
    namespace = {'re': re, 'collections': collections}
    exec(compile(parser, '<unchanged-frozen-report-parser>', 'exec'), namespace)
    coverage = {}
    for scope, recorded, directory, previous in (
        ('fit', summary, 'timing', json.loads(old['fit/summary.json'])),
        ('original-sdc', original, 'reports', json.loads(old['original-sdc/summary.json']))):
        actual_reports = {name.removeprefix(scope + '/' + directory + '/'): sha(raw)
                          for name, raw in data.items() if name.startswith(scope + '/' + directory + '/')}
        check(actual_reports == recorded['report_hashes'], 'Full raw report inventory differs: ' + scope)
        check(set(recorded['corners']) == CORNERS, 'Corner population differs')
        coverage[scope] = {}
        for corner, kinds in recorded['corners'].items():
            for kind, groups in kinds.items():
                for group, row in groups.items():
                    raw = data[f'{scope}/{directory}/{corner}/{group}_{kind}.rpt']
                    parsed = namespace['parse_report'](ActualReportText(raw))
                    check(parsed['reported_paths'] == row['tool_path_count'], 'Raw path count differs')
                    check(parsed['top_paths'][0]['slack_ns'] == row['tool_worst_slack_ns'], 'Raw slack differs')
                    if group == 'global':
                        header = raw.decode().split('Path #1:', 1)[0]
                        check('report_timing -' + kind in header and
                              not re.search(r'\s-(from|to|from_clock|to_clock)\s', header), 'Filtered global report')
            check(recorded['corner_metadata'][corner]['check_timing_issues'] ==
                  previous['corner_metadata'][corner]['check_timing_issues'], 'Inherited timing coverage changed')
            check(recorded['corner_metadata'][corner]['unclocked_node_families'] ==
                  previous['corner_metadata'][corner]['unclocked_node_families'], 'Unclocked scope changed')
            raw = data[f'{scope}/{directory}/{corner}/unconstrained.rpt'].decode()
            values = {row[0]: [int(value) for value in row[1:]] for row in
                      namespace['table_rows'](raw.split('; Clock Status Summary', 1)[0])
                      if len(row) == 3 and row[1].isdigit() and row[2].isdigit()}
            check(values.get('Illegal Clocks') == values.get('Unconstrained Clocks') == [0, 0], 'Clock coverage issue')
            coverage[scope][corner] = values
    groups = set(summary['corners']['7_slow_1100mv_100c']['setup'])
    check(len(groups) == 17 and all(set(values[kind]) == groups for values in summary['corners'].values()
                                  for kind in ('setup', 'hold')), 'Missing setup/hold selector')
    for prefix in ('macro=', 'clock='):
        lines = data['fit/timing/collections.txt'].decode().splitlines()
        old_lines = old['fit/timing/collections.txt'].decode().splitlines()
        check(sorted(line for line in lines if line.startswith(prefix)) ==
              sorted(line for line in old_lines if line.startswith(prefix)), 'Feature/clock collections changed')
    fit_report = data['fit/work/output_files/PCAT-286.fit.rpt'].decode('latin1')
    check(re.findall(r'(?m)^set_global_assignment -name SEED\s+(\d+)\s*$',
                     data['effective-source/PCAT-286.qsf'].decode()) == ['2'] and
          re.findall(r'; Fitter Initial Placement Seed\s*;\s*(\d+)\s*;', fit_report) == ['2'], 'Actual seed differs')
    check('set_min_delay -from $at_dac_write_index -to $at_dac_write_address 0.500' in
          data['effective-source/SYSTEM.sdc'].decode(), 'Supplemental palette constraint removed')
    check('AT SDC DAC minimum route: 8 sources, 288 endpoints' in data['fit/compile.log'].decode(), 'Compile palette selectors absent')
    check(len(om['preserved_fitted_artifacts_sha256']) == 11, 'Original-SDC artifact population differs')
    fit_dir = ROOT / result['candidate']
    for name, digest in om['preserved_fitted_artifacts_sha256'].items():
        check(sha((fit_dir / 'work' / name).read_bytes()) == digest, 'Same fitted artifact drift: ' + name)
    check('All original fitted artifacts verified unchanged after original-SDC STA' in
          data['original-sdc/original-artifacts-verified.log'].decode(), 'Original-SDC artifact seal absent')
    rom = result['compiled_rom']
    mif_bytes = data['compiled-rom/' + rom['mif']]
    words = load('effective-source/vendor/spk286/tests/fixtures/microcode_esc_boundary.json')['words']
    entries = re.findall(r'^\s*(\d+)\s*:\s*([01]{9})\s*;\s*$', mif_bytes.decode(), re.M)
    check(len(words) == 743 and len(entries) == 1024 and {int(address) for address, _ in entries} == set(range(1024)), 'Mapped ROM shape differs')
    check(all(int(value, 2) == ((256 | words[int(address)]) if int(address) < 743 else 0)
              for address, value in entries), 'Mapped ROM words differ')
    check(sha(mif_bytes) == rom['mif_sha256'], 'Mapped ROM SHA differs')
    compile_text = data['fit/compile.log'].decode()
    match = re.search(r'Info \(12133\): Instantiated megafunction [^\n]*spk286_microcode_sync_rom[^\n]*\n'
                      r'((?:\s*Info \(12134\): Parameter [^\n]*\n)+)', compile_text)
    check(match is not None, 'Compiled primitive parameters absent')
    parameters = dict(re.findall(r'Parameter "([A-Z0-9_]+)" = "([^"]*)"', match.group(1)))
    check(parameters == rom['parameters'], 'Reported mapped ROM parameters differ')
    for name, value in {'OPERATION_MODE': 'ROM', 'WIDTH_A': '9', 'WIDTHAD_A': '10', 'NUMWORDS_A': '1024',
                        'OUTDATA_REG_A': 'UNREGISTERED', 'ADDRESS_ACLR_A': 'NONE', 'RAM_BLOCK_TYPE': 'M10K'}.items():
        check(parameters[name] == value, 'ROM primitive alignment differs')
    labels = {'equivalent_alms': 'Logic utilization (in ALMs)', 'registers': 'Total registers',
              'memory_bits': 'Total block memory bits', 'm10k': 'Total RAM Blocks', 'dsp': 'Total DSP Blocks', 'plls': 'Total PLLs'}
    fit_summary = data['fit/work/output_files/PCAT-286.fit.summary'].decode('latin1')
    resource = {key: int(re.search(r'(?m)^' + re.escape(label) + r'\s*:\s*([\d,]+)', fit_summary)[1].replace(',', ''))
                for key, label in labels.items()}
    resource['placed_alms'] = int(re.search(r'ALMs used in final placement \[=a\+b\+c\+d\]\s*;\s*([\d,]+)', fit_report)[1].replace(',', ''))
    check(all(result['resources'][key] == value for key, value in resource.items()), 'Actual placed resources differ')
    resource_parser = ast.parse(data['effective-source/scripts/analyze_pcat_resources.py'])
    resource_parser.body = [node for node in resource_parser.body if isinstance(node, ast.FunctionDef) and
                           node.name in ('amount', 'parse')]
    resource_namespace = {'re': re}
    exec(compile(resource_parser, '<unchanged-frozen-hierarchy-parser>', 'exec'), resource_namespace)
    hierarchy = resource_namespace['parse'](ActualReportText(data['fit/work/output_files/PCAT-286.fit.rpt']))
    check(hierarchy == load('hierarchy.json'), 'Archived hierarchy differs from actual fitter report')
    cpu = next(row for row in hierarchy if row['path'].endswith('|spk286_profiled:cpu'))
    check(result['resources']['cpu'] == {key: cpu[key]['inclusive'] for key in result['resources']['cpu']}, 'CPU hierarchy resource identity differs')
    margins = {kind: minimum(summary, kind) for kind in ('setup', 'hold', 'recovery', 'removal')}
    originals = {kind: minimum(original, kind) for kind in margins}
    check(result['with_extra_route_requirement'] == {key: list(value) for key, value in margins.items()} and
          result['same_fit_original_sdc'] == {key: list(value) for key, value in originals.items()}, 'Global margins differ')
    check(margins['setup'][0] == -0.063 and margins['hold'][0] == 0.027 and
          result['status'] == 'TIMING_OPEN_CHECK_REPORTED_MARGINS', 'Incorrect closure claim')
    check(result['full_regression'] == before['full_regression'] == after['full_regression'] ==
          'USER_PAUSE_AFTER_CURRENT_FIT_NOT_RUN', 'Latest pause lost')
    sta = data['fit/work/output_files/PCAT-286.sta.summary'].decode('latin1')
    sta_rows = [(match[1], float(match[2]), float(match[3])) for match in re.finditer(
        r'Type\s*:\s*(.+?)\nSlack\s*:\s*(-?[\d.]+)\nTNS\s*:\s*(-?[\d.]+)', sta)]
    check(len(sta_rows) > 50 and any('Minimum Pulse Width' in name for name, _, _ in sta_rows), 'Physical STA pulse inventory absent')
    check(result['sta_summary_rows'] == [{'type': name, 'slack_ns': slack, 'tns_ns': tns} for name, slack, tns in sta_rows], 'Physical STA summary rows differ')
    rbf = ROOT / result['rbf']['path']
    check(rbf.stat().st_size == result['rbf']['bytes'] == 4156532 and
          sha(rbf.read_bytes()) == result['rbf']['sha256'] ==
          'd83a6d9494f69e68d9236bf7555c05f2fa344c3f1ab46208c8225a727fef40de', 'RBF identity differs')
    current = load_file(ROOT / 'docs/imports/current-spk286.json')
    live_drift = [name for name in sources if name.endswith(hardware_suffixes) and name != 'build_id.v' and
                  (ROOT / name).is_file() and sha((ROOT / name).read_bytes()) != sources[name]]
    check(set(live_drift) <= {'PCAT-286.qsf'}, 'Live active HDL/settings drift')
    physical_setting_overlay = None
    if live_drift:
        live_qsf = (ROOT / 'PCAT-286.qsf').read_bytes()
        line1 = b'set_global_assignment -name SEED 1\n'
        line2 = b'set_global_assignment -name SEED 2\n'
        check(live_qsf.count(line1) == 1 and
              live_qsf.replace(line1, line2, 1) == data['effective-source/PCAT-286.qsf'],
              'Live QSF differs beyond the explicit placement-seed overlay')
        physical_setting_overlay = {'path': 'PCAT-286.qsf', 'live_sha256': sha(live_qsf),
            'fitted_sha256': sources['PCAT-286.qsf'],
            'rule': 'Exact single literal SEED 1 to SEED 2 line; all other live QSF bytes identical.'}
    parent_result = json.loads(old['result.json'])
    review = {
        'status': 'INDEPENDENT_ACTUAL_FIT_REVIEW_PASS_TIMING_STILL_OPEN',
        'scope': 'Read-only complete archive/report/source/constraint/placed-resource/ROM/bitstream review; no tests, fit, STA or regression executed.',
        'archive_sha256': manifest['sha256'], 'archive_bytes': (PACKET / manifest['archive']).stat().st_size,
        'members_readback': manifest['members'], 'frozen_sources': len(sources), 'seed': 2,
        'canonical_imports': 1249, 'canonical_upstream': ledger['upstream_head'],
        'current_imports': len(current['imported']), 'current_upstream': current['upstream_head'],
        'live_active_rtl_changes': [], 'physical_setting_overlay': physical_setting_overlay,
        'global_margins_ns': margins,
        'original_sdc_margins_ns': originals, 'groups': result['allgroups'], 'coverage': coverage,
        'resources': result['resources'], 'baseline_resources': parent_result['resources'],
        'resource_delta': {key: result['resources'][key] - parent_result['resources'][key] for key in resource},
        'compiled_microcode': rom, 'rbf': result['rbf'],
        'corner_global_setup': {corner: values['setup']['global']['tool_worst_slack_ns']
                               for corner, values in summary['corners'].items()},
        'worst_setup_path': summary['corners'][margins['setup'][1]]['setup']['global']['top_paths'][0],
        'full_regression': 'USER_PAUSE_AFTER_CURRENT_FIT_NOT_RUN', 'hardware': 'NOT_RUN', 'closure': False,
        'review_script_sha256': sha(Path(__file__).read_bytes()),
    }
    output.write_text(json.dumps(review, indent=2) + '\n', encoding='utf-8', newline='\n')
    markdown = '# Independent actual fit review\n\n'
    markdown += 'Status: **PASS for evidence integrity; global timing remains open**. No test, fit, STA or regression was launched by this review.\n\n'
    markdown += f"All {manifest['members']} archived members were read back. The fitted snapshot contains 2,073 sources and 1,249 canonical vendor imports, with seed 2.\n\n"
    markdown += '| Check | Worst margin (ns) |\n| --- | ---: |\n'
    markdown += ''.join(f'| {kind} | {value[0]:+.3f} |\n' for kind, value in margins.items())
    markdown += '\nThe remaining setup path is scaler `o_ihsize[3]` to `o_hacc_next[12]` at the cold slow corner. CPU, common 50 MHz paths, buffers and SDRAM selectors are positive.\n\n'
    markdown += 'All features, clocks and constraints match the accepted parent; original-SDC STA uses the same eleven fitted DB/RBF/SOF artifacts. Actual mapped ROM contents and read-alignment parameters match the frozen contract.\n\n'
    if physical_setting_overlay:
        markdown += 'The only live/frozen physical-setting difference is the declared single-line placement seed 1 to 2 overlay; every other QSF byte is identical. No active HDL/config/SDC drift is present.\n\n'
    markdown += f"Resources: {resource['equivalent_alms']:,} equivalent ALMs, {resource['placed_alms']:,} placed ALMs; {resource['registers']:,} registers, {resource['m10k']} M10Ks, {resource['dsp']} DSP blocks and {resource['plls']} PLLs.\n\n"
    markdown += 'The latest user instruction remains **pause after this fit**. Full regression and hardware validation are unrun; no global closure is claimed.\n'
    (OWN / 'review.md').write_text(markdown, encoding='utf-8', newline='\n')
    print('INDEPENDENT_ACTUAL_FIT_REVIEW_PASS_TIMING_STILL_OPEN', margins, manifest['members'])


if __name__ == '__main__':
    main()
