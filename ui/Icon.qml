// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Window

// Tinted SVG icon. Falls back to the plain file when the tint provider is not
// registered (development QA harnesses load Main.qml without it).
//
// The box size comes only from `size`. A bare Image reports its pixel size as
// its implicit size, and layouts size items from implicit sizes: on a 150-200%
// Windows display width → sourceSize → pixels → width doubled on every pass
// until the window froze when edit mode showed its hint icon (0.9.3–0.9.7).
Item {
    id: icon
    property string name: ""
    property color tone: Theme.icon
    property real size: 18
    // "iconTint" is set by the application when the tint provider exists.
    property bool plain: typeof iconTint === "undefined"
    readonly property int pixels: Math.max(1, Math.ceil(size * Screen.devicePixelRatio))
    width: size; height: size
    implicitWidth: size; implicitHeight: size
    visible: name.length > 0
    Image {
        anchors.fill: parent
        smooth: true; mipmap: true
        fillMode: Image.PreserveAspectFit
        sourceSize: Qt.size(icon.pixels, icon.pixels)
        source: !icon.name.length ? "" : icon.plain ? "../assets/icons/" + icon.name + ".svg" : Theme.iconUrl(icon.name, icon.tone)
        onStatusChanged: if (status === Image.Error && !icon.plain) icon.plain = true
    }
}
