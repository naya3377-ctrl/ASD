// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Window

// The 윤DF mark: an ink-charcoal Y on a white rounded tile with a hairline
// edge, drawn from the vector made by scripts/make_logo.py so it is crisp at
// any size and screen scale. `size` is the edge length.
Item {
    id: mark
    property real size: 24
    width: size; height: size
    implicitWidth: size; implicitHeight: size
    Image {
        anchors.fill: parent
        source: "../assets/logo/mark.svg"
        sourceSize: Qt.size(Math.ceil(mark.size * Screen.devicePixelRatio), Math.ceil(mark.size * Screen.devicePixelRatio))
        smooth: true
    }
}
