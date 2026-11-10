#!/usr/bin/env python3
"""Generate and optionally sign the complete iPhone workflow (macOS required to sign).

Serialization reference: https://github.com/electrikmilk/cherri
Apple signing: https://support.apple.com/guide/shortcuts-mac/apd455c82f02/mac
No third-party compiler or signing service is required.
"""
import argparse
import plistlib
import subprocess
from pathlib import Path
from uuid import uuid4


def uid():
    return str(uuid4()).upper()


def action(identifier, **parameters):
    return {'WFWorkflowActionIdentifier': identifier,
            'WFWorkflowActionParameters': parameters}


def attachment(value):
    return {'Value': value, 'WFSerializationType': 'WFTextTokenAttachment'}


def workflow(bundle, name, team_id="0000000000"):
    actions = []

    def intent(identifier, output_name, **parameters):
        reference = uid()
        actions.append(action(f'{bundle}.{identifier}',
            AppIntentDescriptor={'TeamIdentifier': team_id,
                'BundleIdentifier': bundle, 'Name': name,
                'AppIntentIdentifier': identifier},
            UUID=reference, CustomOutputName=output_name, **parameters))
        return attachment({'Type': 'ActionOutput', 'OutputUUID': reference,
                           'OutputName': output_name})

    def begin_if(output):
        group = uid()
        actions.append(action('is.workflow.actions.conditional',
            GroupingIdentifier=group, WFControlFlowMode=0,
            WFInput={'Type': 'Variable', 'Variable': output},
            WFCondition=4, WFNumberValue=1))
        return group

    def end_if(group):
        actions.append(action('is.workflow.actions.conditional',
            GroupingIdentifier=group, WFControlFlowMode=2, UUID=uid()))

    actions.append(action('is.workflow.actions.comment', WFCommentActionText=
        '先安装支持自动化动作的 WrapPin，并完成配对及收藏。每次运行选择收藏点。'
        '运行时保持解锁；结束时蜂窝数据保持开启。若手动取消或系统中断，'
        '请手动开启蜂窝并恢复真实位置。五秒不代表飞书已完成定位。'))
    preparation = intent('PrepareFavouriteAutomationIntent', '需要关闭蜂窝',
                         place=attachment({'Type': 'Ask'}))
    group = begin_if(preparation)
    actions.append(action('is.workflow.actions.cellulardata.set',
                          OnValue=False, operation='set'))
    end_if(group)
    ready = intent('WaitForFavouriteAutomationIntent', '模拟成功')
    # Unconditional restoration must precede branching on the connection result.
    actions.append(action('is.workflow.actions.cellulardata.set',
                          OnValue=True, operation='set'))
    group = begin_if(ready)
    actions.append(action('is.workflow.actions.openapp',
        WFAppIdentifier='com.bytedance.ee.lark',
        WFSelectedApp={'BundleIdentifier': 'com.bytedance.ee.lark', 'Name': '飞书'}))
    actions.append(action('is.workflow.actions.delay', WFDelayTime=5))
    end_if(group)
    intent('RestoreRealLocationIntent', '恢复结果')
    return {
        'WFWorkflowName': f'{name} 收藏点到飞书',
        'WFWorkflowClientVersion': '3036.0.4.2',
        'WFWorkflowMinimumClientVersion': 900,
        'WFWorkflowMinimumClientVersionString': '900',
        'WFWorkflowIcon': {'WFWorkflowIconStartColor': 4282601983,
                           'WFWorkflowIconGlyphNumber': 59511},
        'WFWorkflowActions': actions,
        'WFWorkflowImportQuestions': [],
        'WFWorkflowInputContentItemClasses': [],
        'WFWorkflowOutputContentItemClasses': [],
        'WFWorkflowTypes': [],
        'WFQuickActionSurfaces': [],
        'WFWorkflowHasShortcutInputVariables': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-id', default='com.suversal.wrappin')
    parser.add_argument('--name', default='WrapPin')
    parser.add_argument('--team-id', default='0000000000')
    parser.add_argument('--output', type=Path, default=Path('Shortcuts/WrapPin-Feishu.shortcut'))
    parser.add_argument('--sign', action='store_true', help='Sign via Apple for import on iPhone')
    args = parser.parse_args()
    data = workflow(args.bundle_id, args.name, args.team_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    unsigned = args.output.with_suffix('.unsigned.shortcut') if args.sign else args.output
    unsigned.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_XML, sort_keys=False))
    if args.sign:
        subprocess.run(['shortcuts', 'sign', '--mode', 'anyone',
                        '--input', str(unsigned), '--output', str(args.output)], check=True)
    print(args.output)


if __name__ == '__main__':
    main()
