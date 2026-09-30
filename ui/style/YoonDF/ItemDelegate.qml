// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.ItemDelegate {
    id: control
    font.pixelSize: 14
    contentItem: Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
        text: control.text; font: control.font; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
        color: control.highlighted ? Theme.inkOnAccent : Theme.ink
    }
    background: Rectangle {
        radius: Theme.radiusSmall
        color: control.highlighted ? Theme.accent : control.hovered ? Theme.hover : "transparent"
    }
}
