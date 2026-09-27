// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A segmented control: a shallow grey groove with the chosen segment on a
// white pill that glides to it in 140 ms. Children are ActionButtons with
// `tab: true`; the one whose `active` is true is chosen. Each segment keeps
// the full 32 px height as its click area; the pill is drawn inside it.
Rectangle {
    id: groove
    default property alias content: row.data
    readonly property Item current: {
        for (var i = 0; i < row.children.length; ++i)
            if (row.children[i].active) return row.children[i];
        return null;
    }
    implicitWidth: row.implicitWidth + 4; implicitHeight: Theme.control
    radius: Theme.radius+1; color: Theme.well
    Rectangle {
        id: pill; visible: !!groove.current
        x: groove.current ? row.x + groove.current.x : 2; y: 2
        width: groove.current ? groove.current.width : 0; height: groove.height - 4
        radius: Theme.radius-1; color: Theme.raised
        border.color: Theme.line; border.width: Theme.hairline
        Behavior on x { NumberAnimation { duration: Theme.selectMs; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.selectMs; easing.type: Easing.OutCubic } }
    }
    Row { id: row; x: 2; y: 0; spacing: 0; height: groove.height }
}
