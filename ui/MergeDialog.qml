// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Dialog {
    id: dialog; objectName: "mergeDialog"
    property var controller: bridge
    width: Math.min(780,parent.width-60); height: Math.min(650,parent.height-60)
    anchors.centerIn: parent; modal: true; padding: 22
    onClosed: controller.closeMerge()
    closePolicy: controller.mergeBusy ? Popup.NoAutoClose : Popup.CloseOnEscape
    background: Block { fill: Theme.raised; radius: Theme.radiusLarge+2; shadow: "large" }
    Overlay.modal: Rectangle { color: Theme.scrim }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.smooth; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: .96; to: 1; duration: Theme.smooth; easing.type: Easing.OutCubic }
    }
    header: Item {
        height: 88
        Row {
            x: 22; y: 22; spacing: 12
            BrandMark { size: 44; anchors.verticalCenter: parent.verticalCenter }
            Column {
                anchors.verticalCenter: parent.verticalCenter; spacing: 4
                Text { text: "PDF 결합"; font.pixelSize: Theme.title3; font.weight: Font.Bold; color: Theme.ink }
                Text { text: "여러 문서를 원하는 순서로 하나의 PDF에 담으세요."; font.pixelSize: Theme.small; color: Theme.inkMuted }
            }
        }
        ActionButton { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 17; glyph: "close"; hint: "닫기"; enabled: !controller.mergeBusy; onClicked: dialog.close() }
    }
    contentItem: ColumnLayout {
        spacing: 14
        RowLayout {
            spacing: 8
            ActionButton { objectName: "mergeAddFiles"; glyph: "add"; text: "PDF 추가"; outlined: true; enabled: !controller.mergeBusy; onClicked: controller.chooseMergeFiles() }
            ActionButton { glyph: "open"; text: "현재 문서 추가"; enabled: !controller.mergeBusy && controller.document.count>0; onClicked: controller.addCurrentToMerge() }
            Item { Layout.fillWidth: true }
            Text { text: controller.mergeItems.length+"개 파일  ·  "+controller.mergePageCount+"페이지"; font.features: ({ "tnum": 1 }); font.pixelSize: Theme.small; color: Theme.inkMuted }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.sidebar; radius: Theme.radiusLarge; border.color: Theme.lineSoft; border.width: Theme.hairline
            ListView {
                id: list; objectName: "mergeList"; anchors.fill: parent; anchors.margins: 10
                clip: true; spacing: 8; model: controller.mergeItems
                ScrollBar.vertical: AppScrollBar { }
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: list.width-8; height: 80; radius: Theme.radius+2; color: Theme.raised; border.color: Theme.lineSoft; border.width: Theme.hairline
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 14
                        Text { text: index+1; font.features: ({ "tnum": 1 }); font.pixelSize: Theme.small; font.weight: Font.Bold; color: Theme.inkMuted; Layout.preferredWidth: 18; horizontalAlignment: Text.AlignRight }
                        Rectangle {
                            Layout.preferredWidth: 42; Layout.preferredHeight: 56; color: "white"; border.color: Theme.lineSoft; radius: 2
                            Image { anchors.fill: parent; anchors.margins: 1; source: modelData.preview; fillMode: Image.PreserveAspectFit; asynchronous: true }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Text { text: modelData.name; font.pixelSize: Theme.callout; font.weight: Font.DemiBold; color: Theme.ink; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Text { text: modelData.count+"페이지"+(modelData.live ? "  ·  현재 편집 내용 포함" : ""); font.pixelSize: Theme.small; color: Theme.inkMuted }
                        }
                        ActionButton { glyph: "up"; hint: "앞으로"; enabled: !controller.mergeBusy && index>0; onClicked: controller.moveMergeItem(index,index-1) }
                        ActionButton { glyph: "down"; hint: "뒤로"; enabled: !controller.mergeBusy && index<controller.mergeItems.length-1; onClicked: controller.moveMergeItem(index,index+1) }
                        ActionButton { glyph: "close"; hint: "목록에서 제거"; enabled: !controller.mergeBusy; onClicked: controller.removeMergeItem(index) }
                    }
                }
            }
            Column {
                visible: controller.mergeItems.length===0; anchors.centerIn: parent; spacing: 12
                Icon { size: 36; name: "merge"; anchors.horizontalCenter: parent.horizontalCenter; opacity: .65 }
                Text { text: "결합할 PDF를 이곳에 끌어 놓으세요"; color: Theme.inkMuted; font.pixelSize: Theme.callout }
            }
            DropArea { anchors.fill: parent; enabled: !controller.mergeBusy; onDropped: function(drop) { if(drop.hasUrls) controller.addMergePaths(drop.urls); } }
        }
        Text { Layout.fillWidth: true; text: controller.mergeResult ? "결합한 PDF를 저장했어요." : controller.mergeBusy ? controller.mergeProgress : controller.mergeInspecting ? "파일과 미리보기를 확인하고 있어요…" : "위에서 아래 순서로 결합합니다. 원본 파일은 그대로 유지됩니다."; color: controller.mergeResult ? Theme.ink : Theme.inkMuted; font.pixelSize: Theme.small; elide: Text.ElideMiddle }
        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { running: controller.mergeBusy || controller.mergeInspecting; visible: running; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
            Item { Layout.fillWidth: true }
            ActionButton { text: controller.mergeBusy ? "결합 취소" : "닫기"; onClicked: controller.mergeBusy ? controller.cancelMerge() : dialog.close() }
            ActionButton { visible: !controller.mergeResult; objectName: "mergeSaveButton"; text: "결합하여 저장"; primary: true; enabled: controller.mergeItems.length>=2 && !controller.mergeBusy && !controller.mergeInspecting; onClicked: controller.chooseMergeOutput() }
            ActionButton { visible: !!controller.mergeResult; text: "결합한 PDF 열기"; primary: true; onClicked: { var path=controller.mergeResult; dialog.close(); controller.openPath(path); } }
        }
    }
}
