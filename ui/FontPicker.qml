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
    implicitWidth: 260; implicitHeight: 36
    contentItem: Text { text: picker.text+"  ▾"; color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; leftPadding: 10; rightPadding: 10; font.pixelSize: Theme.body }
    background: Rectangle { color: picker.hovered ? Theme.hover : Theme.field; border.color: Theme.lineStrong; border.width: popup.visible ? Theme.borderStrong : Theme.border }
    onClicked: {popup.open();fontSearch.forceActiveFocus();}
    Popup {
        id: popup; objectName: "fontSearchPopup"; y: picker.height+5
        width: Math.max(320,picker.width); height: Math.min(440, picker.Window.window.height-210)
        padding: 10; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        background: Block { fill: Theme.surface }
        ColumnLayout {
            anchors.fill: parent; spacing: 8
            TextField { id: fontSearch; objectName: "fontSearchInput"; Layout.fillWidth: true; placeholderText: "글꼴 이름 검색 · 한글 / 영문"; selectByMouse: true; onAccepted: {if(fontList.count){picker.controller.setFontChoice(fontList.model[fontList.currentIndex<0 ? 0 : fontList.currentIndex].key);popup.close();}} }
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
                    objectName: "fontResult"+index; width: fontList.width; text: modelData.label
                    highlighted: index===fontList.currentIndex
                    onClicked: {picker.controller.setFontChoice(modelData.key);popup.close();}
                }
                Text { visible: fontList.count===0; anchors.centerIn: parent; text: "일치하는 글꼴이 없어요"; color: Theme.inkMuted }
            }
        }
        onClosed: fontSearch.text=""
    }
}
