// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A bordered block with a hard offset shadow, the basic Bauhaus surface.
// Children go on the face. `pressed` pushes the face into its shadow,
// `lifted` raises it slightly (hover on cards).
Item {
    id: block
    default property alias content: face.data
    property color fill: Theme.raised
    property color outline: Theme.lineStrong
    property int outlineWidth: Theme.border
    property int shadow: Theme.shadowSmall
    property color shadowColor: Theme.shadow
    property bool pressed: false
    property bool lifted: false
    property real radius: 0
    readonly property alias face: face
    Rectangle {
        visible: block.shadow > 0 && !block.pressed
        x: block.shadow; y: block.shadow; width: block.width; height: block.height
        radius: block.radius; color: block.shadowColor
    }
    Rectangle {
        id: face
        width: block.width; height: block.height; radius: block.radius
        x: block.pressed ? Math.min(2, block.shadow) : 0
        y: block.pressed ? Math.min(2, block.shadow) : block.lifted ? -2 : 0
        color: block.fill; border.color: block.outline; border.width: block.outlineWidth
        Behavior on y { NumberAnimation { duration: Theme.snap; easing.type: Easing.OutCubic } }
    }
}
