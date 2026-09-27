// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A rounded card: a raised face with a hairline edge and, when asked, a soft
// shadow. Children go on the face.
Item {
    id: block
    default property alias content: face.data
    property color fill: Theme.raised
    property color outline: Theme.lineSoft
    property real outlineWidth: Theme.hairline
    property real radius: Theme.radiusLarge
    property string shadow: ""        // "", small, medium, large
    readonly property alias face: face
    Shadow { target: face; level: block.shadow || "small"; visible: block.shadow.length > 0 }
    Rectangle {
        id: face
        width: block.width; height: block.height; radius: block.radius
        color: block.fill; border.color: block.outline; border.width: block.outlineWidth
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    }
}
