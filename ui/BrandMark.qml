// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Window

// The 윤DF mark: the character on indigo denim with tan stitching, the same
// rounded square as the application icon (drawn by scripts/make_logo.py).
// `size` is the edge length.
Item {
    id: mark
    property real size: 24
    readonly property int pixels: Math.ceil(size * Screen.devicePixelRatio)
    width: size; height: size
    implicitWidth: size; implicitHeight: size
    Image {
        anchors.fill: parent
        source: "../assets/icon/" + (mark.pixels <= 32 ? 32 : mark.pixels <= 64 ? 64 : mark.pixels <= 128 ? 128 : mark.pixels <= 256 ? 256 : 512) + ".png"
        smooth: true; mipmap: true
    }
}
