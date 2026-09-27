// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every menu: a white rounded panel with a hairline edge and a soft popup
// shadow. It opens in 150 ms (fading in while its rows settle 4 px upward)
// and fades out in 100 ms. While it fades out it takes no clicks, so nothing
// lands on a menu that is already going away. Items are AppMenuItem and
// AppMenuSeparator.
Menu {
    id: menu
    property bool accepting: false
    property real shift: 0
    padding: 5
    font.family: Theme.family
    font.pixelSize: Theme.body
    implicitWidth: Math.max(200, contentWidth + leftPadding + rightPadding)
    onAboutToShow: accepting = true
    onAboutToHide: accepting = false
    delegate: AppMenuItem { }
    contentItem: Item {
        implicitWidth: list.implicitWidth; implicitHeight: list.implicitHeight
        ListView {
            id: list; anchors.fill: parent
            implicitHeight: contentHeight
            implicitWidth: { var w = 0; for (var i = 0; i < menu.count; ++i) { var it = menu.itemAt(i); if (it) w = Math.max(w, it.implicitWidth); } return w; }
            model: menu.contentModel
            interactive: Window.window ? contentHeight + menu.topPadding + menu.bottomPadding > menu.height : false
            clip: true
            currentIndex: menu.currentIndex
            transform: Translate { y: menu.shift }
            ScrollIndicator.vertical: ScrollIndicator { }
        }
        // Swallows pointer input only while the menu is closing.
        MouseArea { anchors.fill: parent; enabled: !menu.accepting; hoverEnabled: true; acceptedButtons: Qt.AllButtons }
    }
    background: Block { implicitWidth: 200; fill: Theme.raised; radius: Theme.radiusLarge; shadow: "medium"; outline: Theme.line }
    enter: Transition {
        ParallelAnimation {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
            NumberAnimation { target: menu; property: "shift"; from: Theme.menuShift; to: 0; duration: Theme.menuInMs; easing.type: Easing.OutCubic }
        }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; to: 0; duration: Theme.menuOutMs; easing.type: Easing.OutCubic }
    }
}
