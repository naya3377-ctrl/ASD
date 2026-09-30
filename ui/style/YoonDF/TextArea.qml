// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.TextArea {
    id: control
    padding: 8
    font.pixelSize: 14
    color: Theme.ink
    placeholderTextColor: Theme.inkMuted
    selectionColor: Theme.selection; selectedTextColor: Theme.ink
}
