// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool active: false
    property bool primary: false
    property bool outlined: false
    property bool leftAligned: false
    property string glyph: ""
    property string hint: ""
    implicitHeight: 36
    implicitWidth: contentItem.implicitWidth + (text.length ? 24 : 18)
    leftPadding: 12; rightPadding: 12
    font.pixelSize: 13
    font.weight: primary || active ? Font.DemiBold : Font.Normal
    hoverEnabled: true
    opacity: enabled ? 1 : .4
    contentItem: Item {
        implicitWidth: contentRow.implicitWidth; implicitHeight: 20
        Row {
            id: contentRow; spacing: 7; anchors.verticalCenter: parent.verticalCenter
            x: control.leftAligned ? 0 : (parent.width-width)/2
            Image { visible: control.glyph.length>0; width: visible ? 18 : 0; height: 18; anchors.verticalCenter: parent.verticalCenter; source: visible ? "../assets/icons/"+control.glyph+".svg" : ""; smooth: true }
            Text { visible: control.text.length>0; text: control.text; font: control.font; color: control.primary ? "#ffffff" : control.active ? "#234d42" : "#465358"; anchors.verticalCenter: parent.verticalCenter }
        }
    }
    background: Rectangle {
        radius: 7
        color: control.primary ? (control.down ? "#183b32" : control.hovered ? "#346454" : "#284f43") : control.down ? "#e3e8e6" : control.active ? "#e7efeb" : control.hovered ? "#edf0ee" : control.outlined ? "#ffffff" : "transparent"
        border.width: control.outlined ? 1 : 0
        border.color: "#dce2df"
    }
    ToolTip.visible: hovered && hint.length>0
    ToolTip.text: hint; ToolTip.delay: 600
}
