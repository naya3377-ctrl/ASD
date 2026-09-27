// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A square black bar on a hairline track; widens while held.
ScrollBar {
    id: bar
    padding: 2
    contentItem: Rectangle {
        implicitWidth: bar.pressed ? 10 : 7; implicitHeight: bar.pressed ? 10 : 7
        color: bar.pressed ? Theme.blue : Theme.lineStrong
        opacity: bar.policy === ScrollBar.AlwaysOn || bar.active || bar.hovered ? 1 : .0
        Behavior on opacity { NumberAnimation { duration: Theme.snap } }
    }
    background: Item { }
}
