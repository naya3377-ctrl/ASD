// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A hairline between groups of menu rows.
MenuSeparator {
    topPadding: 4; bottomPadding: 4; leftPadding: 8; rightPadding: 8
    contentItem: Rectangle { implicitWidth: 180; implicitHeight: Theme.hairline; color: Theme.line }
}
