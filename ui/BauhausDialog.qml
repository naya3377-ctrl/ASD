// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every dialog: a black title bar with a primary mark, a heavy frame and a
// hard shadow. Standard buttons use ActionButton; the accepting one is red.
Dialog {
    id: dialog
    property color markColor: Theme.red
    padding: 22; topPadding: 20
    background: Block { fill: Theme.surface; outlineWidth: Theme.borderHeavy; shadow: Theme.shadowLarge+2 }
    header: Rectangle {
        implicitHeight: 48; color: Theme.black
        visible: dialog.title.length > 0
        Row {
            x: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 12
            Geo { kind: "square"; size: 12; color: dialog.markColor; anchors.verticalCenter: parent.verticalCenter }
            Text { text: dialog.title; font.pixelSize: 15; font.weight: Font.Black; font.letterSpacing: .3; color: Theme.white; anchors.verticalCenter: parent.verticalCenter }
        }
    }
    footer: DialogButtonBox {
        visible: count > 0
        padding: 18; topPadding: 4; spacing: 10
        background: Item { }
        delegate: ActionButton {
            outlined: DialogButtonBox.buttonRole !== DialogButtonBox.AcceptRole
            primary: DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole
            implicitWidth: Math.max(84, implicitContentWidth + 32)
        }
    }
    Overlay.modal: Rectangle { color: "#8c121212" }
}
