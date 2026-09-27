// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every dialog: a white sheet with 12 px corners, a hairline edge and a soft
// popup shadow, a quiet title, buttons at the lower right with the accepting
// one filled. It fades in over 150 ms while its content settles 4 px upward.
// It closes at once: a modal sheet that lingered while fading would swallow
// the next click on the window.
Dialog {
    id: dialog
    property real shift: 0
    padding: Theme.gapXl; topPadding: Theme.gapS
    font.family: Theme.family
    font.pixelSize: Theme.body
    background: Block { fill: Theme.raised; radius: Theme.radiusDialog; shadow: "large"; outline: Theme.line }
    header: Item {
        implicitHeight: dialog.title.length > 0 ? 56 : 0
        visible: dialog.title.length > 0
        Text {
            x: Theme.gapXl; y: 22; width: parent.width-2*Theme.gapXl; elide: Text.ElideRight
            text: dialog.title; font.family: Theme.family; font.pixelSize: Theme.title2; font.weight: Font.DemiBold
            color: Theme.ink
            transform: Translate { y: dialog.shift }
        }
    }
    footer: DialogButtonBox {
        visible: count > 0
        padding: Theme.gapXl; topPadding: Theme.gapXs; spacing: Theme.gapS
        background: Item { }
        delegate: ActionButton {
            outlined: DialogButtonBox.buttonRole !== DialogButtonBox.AcceptRole
            primary: DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole
            implicitWidth: Math.max(84, implicitContentWidth + 32)
        }
    }
    // The content (not the sheet) settles upward as the dialog appears.
    property Translate contentShift: Translate { y: dialog.shift }
    Component.onCompleted: if (contentItem) contentItem.transform = [contentShift]
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
            NumberAnimation { target: dialog; property: "shift"; from: Theme.menuShift; to: 0; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
        }
    }
    Overlay.modal: Rectangle { color: Theme.scrim }
}
