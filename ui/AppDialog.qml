// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every dialog: a white sheet framed by a line, its title set large in the
// display serif over a heavy rule. The accepting button is the black one.
Dialog {
    id: dialog
    padding: 26; topPadding: 22
    background: Block { fill: Theme.surface }
    header: Item {
        implicitHeight: dialog.title.length > 0 ? 78 : 0
        visible: dialog.title.length > 0
        Text {
            x: 26; y: 24; width: parent.width-52; elide: Text.ElideRight
            text: dialog.title; font.family: Theme.displayFamily; font.pixelSize: Theme.title-2; font.weight: Font.Bold
            color: Theme.ink
        }
        Rectangle { x: 26; anchors.bottom: parent.bottom; width: parent.width-52; height: Theme.rule; color: Theme.ink }
    }
    footer: DialogButtonBox {
        visible: count > 0
        padding: 22; topPadding: 4; spacing: 10
        background: Item { }
        delegate: ActionButton {
            outlined: DialogButtonBox.buttonRole !== DialogButtonBox.AcceptRole
            primary: DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole
            implicitWidth: Math.max(88, implicitContentWidth + 32)
        }
    }
    Overlay.modal: Rectangle { color: Theme.scrim }
}
