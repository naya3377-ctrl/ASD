// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: picker; objectName: "fontChoice"
    required property var controller
    property int currentIndex: controller.fontChoiceIndex
    readonly property bool popupOpen: popup.visible
    text: controller.fontOptions[currentIndex] ? controller.fontOptions[currentIndex].label : "글꼴 검색"
    implicitWidth: 240; implicitHeight: Theme.control
    hoverEnabled: true
    leftPadding: 0; rightPadding: 0
    contentItem: Text { text: picker.text; color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; leftPadding: 10; rightPadding: 28; font.pixelSize: Theme.small; font.family: Theme.family }
    background: Rectangle {
        radius: Theme.radius; color: picker.hovered && !popup.visible ? Theme.hover : Theme.field
        border.color: popup.visible ? Theme.focusRing : picker.hovered ? Theme.lineStrong : Theme.line; border.width: popup.visible ? 2 : Theme.hairline
        Icon { x: parent.width-width-10; anchors.verticalCenter: parent.verticalCenter; name: "down"; size: 13; tone: Theme.inkMuted }
    }
    onClicked: {popup.open();fontSearch.forceActiveFocus();}
    Popup {
        id: popup; objectName: "fontSearchPopup"; y: picker.height+5; margins: Theme.gapS
        width: Math.max(320,picker.width); height: Math.min(440, picker.Window.window.height-210)
        padding: Theme.gapS; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        background: Block { fill: Theme.raised; radius: Theme.radiusLarge; shadow: "medium"; outline: Theme.line }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.menuInMs; easing.type: Easing.OutCubic } }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.menuOutMs; easing.type: Easing.OutCubic } }
        ColumnLayout {
            anchors.fill: parent; spacing: Theme.gapS
            TextField {
                id: fontSearch; objectName: "fontSearchInput"; Layout.fillWidth: true; placeholderText: "글꼴 이름 검색 · 한글 / 영문"; selectByMouse: true
                implicitHeight: Theme.control; leftPadding: 10; font.pixelSize: Theme.body; color: Theme.ink; placeholderTextColor: Theme.inkFaint
                selectionColor: Theme.selection; selectedTextColor: Theme.ink
                background: Rectangle { radius: Theme.radius; color: Theme.field; border.width: fontSearch.activeFocus ? 2 : Theme.hairline; border.color: fontSearch.activeFocus ? Theme.focusRing : Theme.line } onAccepted: {if(fontList.count){picker.controller.setFontChoice(fontList.model[fontList.currentIndex<0 ? 0 : fontList.currentIndex].key);popup.close();}} }
            ListView {
                id: fontList; objectName: "fontSearchResults"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                model: {
                    var query=fontSearch.text.trim().toLocaleLowerCase().replace(/\s+/g,"");var rows=picker.controller.fontOptions;
                    if(!query)return rows;
                    return rows.filter(function(row){return (row.label+" "+(row.aliases || []).join(" ")).toLocaleLowerCase().replace(/\s+/g,"").indexOf(query)>=0;});
                }
                ScrollBar.vertical: AppScrollBar {}
                delegate: ItemDelegate {
                    required property var modelData; required property int index
                    objectName: "fontResult"+index; width: fontList.width; height: 32; text: modelData.label
                    highlighted: index===fontList.currentIndex
                    contentItem: Text { text: parent.text; font.pixelSize: Theme.body; font.family: Theme.family; color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; leftPadding: 4 }
                    background: Rectangle { radius: Theme.radius; color: parent.highlighted || parent.hovered ? Theme.accentSoft : "transparent" }
                    onClicked: {picker.controller.setFontChoice(modelData.key);popup.close();}
                }
                Text { visible: fontList.count===0; anchors.centerIn: parent; text: "일치하는 글꼴이 없어요"; color: Theme.inkMuted }
            }
        }
        onClosed: fontSearch.text=""
    }
}
