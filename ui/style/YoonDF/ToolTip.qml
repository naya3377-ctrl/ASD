// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.ToolTip {
    id: control
    padding: 7; leftPadding: 10; rightPadding: 10
    font.pixelSize: 13
    contentItem: Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; text: control.text; font: control.font; color: Theme.ink; wrapMode: Text.WordWrap }
    background: Item {
        SoftShadow { anchors.fill: parent; radius: 7; spread: 6; offsetY: 2 }
        Rectangle { anchors.fill: parent; radius: 7; color: Theme.dark ? "#3a3a3c" : "#fbfbfd"; border.width: 1; border.color: Theme.line }
    }
}
