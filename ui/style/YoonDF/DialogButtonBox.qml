// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.DialogButtonBox {
    id: control
    padding: 16; topPadding: 4; spacing: 8
    alignment: Qt.AlignRight
    delegate: Button {
        highlighted: B.DialogButtonBox.buttonRole === B.DialogButtonBox.AcceptRole || B.DialogButtonBox.buttonRole === B.DialogButtonBox.YesRole
    }
    background: Item { }
}
