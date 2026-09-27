// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// The 윤DF seal: a black sheet with its corner folded away holding 윤 in
// Nanum Myeongjo (drawn by scripts/make_logo.py). `inverse` gives the white
// seal for black bars. `size` is the edge length.
Item {
    id: mark
    property real size: 24
    property bool inverse: false
    width: size; height: size
    implicitWidth: size; implicitHeight: size
    Image {
        anchors.fill: parent
        sourceSize: Qt.size(Math.ceil(mark.size*2), Math.ceil(mark.size*2))
        source: mark.inverse ? "../assets/logo/mark-inverse.svg" : "../assets/logo/mark.svg"
        smooth: true; mipmap: true
    }
}
