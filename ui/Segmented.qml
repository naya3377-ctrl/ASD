// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A macOS segmented control: a shallow groove with the chosen segment raised
// on a white pill that glides to it. Children are ActionButtons with
// `tab: true`; the one whose `active` is true is chosen.
Rectangle {
    id: groove
    default property alias content: row.data
    property real segmentHeight: 26
    readonly property Item current: {
        for (var i = 0; i < row.children.length; ++i)
            if (row.children[i].active) return row.children[i];
        return null;
    }
    implicitWidth: row.implicitWidth + 4; implicitHeight: segmentHeight + 4
    radius: Theme.radius+1; color: Theme.well
    Shadow { target: pill; level: "small"; opacity: .8 }
    Rectangle {
        id: pill; visible: !!groove.current
        x: groove.current ? row.x + groove.current.x : 2; y: 2
        width: groove.current ? groove.current.width : 0; height: groove.segmentHeight
        radius: Theme.radius-1; color: Theme.raised
        border.color: Theme.dark ? "#1affffff" : "#0d2a2420"; border.width: Theme.hairline
        Behavior on x { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
    }
    Row { id: row; x: 2; y: 2; spacing: 0 }
}
