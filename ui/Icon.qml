// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Window

// Tinted SVG icon. Falls back to the plain file when the tint provider is not
// registered (development QA harnesses load Main.qml without it).
Image {
    id: icon
    property string name: ""
    property color tone: Theme.icon
    // "iconTint" is set by the application when the tint provider exists.
    property bool plain: typeof iconTint === "undefined"
    width: 18; height: 18
    visible: name.length > 0
    smooth: true; mipmap: true
    fillMode: Image.PreserveAspectFit
    sourceSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio), Math.ceil(height * Screen.devicePixelRatio))
    source: !name.length ? "" : plain ? "../assets/icons/" + name + ".svg" : Theme.iconUrl(name, tone)
    onStatusChanged: if (status === Image.Error && !plain) plain = true
}
