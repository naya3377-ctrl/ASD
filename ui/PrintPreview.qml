// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

// Print with a preview: settings on the left, the sheets exactly as they will
// come out of the printer on the right. The placement comes from the bridge
// (printLayout), which the print job itself uses, so what you see is what prints.
Popup {
    id: preview
    objectName: "printPreview"
    required property var controller
    parent: Overlay.overlay
    width: parent ? parent.width : 800; height: parent ? parent.height : 600
    modal: true; focus: true; padding: 0
    closePolicy: Popup.CloseOnEscape
    background: Rectangle { color: Theme.canvas }

    // Choices kept while the app runs, so the next print starts where you left.
    property var printerList: []
    property var setup: ({ sizes: [], defaultSize: -1, duplex: false })
    property string printerName: ""
    property int pageSize: -1
    property string range: "all"
    property string custom: ""
    property int copies: 1
    property bool collate: true
    property string orientation: "auto"
    property string fit: "shrink"
    property bool gray: false
    property string duplex: "none"
    property var layout: ({ sheets: [], error: "" })
    property int current: 0
    readonly property bool toPdf: printerName === "__pdf__"
    readonly property var sheets: layout.sheets || []
    readonly property var currentSheet: current >= 0 && current < sheets.length ? sheets[current] : null

    function options() {
        return { printer: printerName, pageSize: pageSize, range: range, custom: custom, copies: copies,
                 collate: collate, orientation: orientation, fit: fit, gray: gray, duplex: duplex };
    }
    function refresh() {
        layout = controller.printLayout(options());
        current = Math.max(0, Math.min(current, sheets.length-1));
    }
    function choosePrinter(name) {
        printerName = name;
        setup = controller.printerSetup(name);
        var keep = false;
        for (var i = 0; i < setup.sizes.length; ++i) if (setup.sizes[i].id === pageSize) keep = true;
        if (!keep) pageSize = setup.defaultSize;
        if (!setup.duplex) duplex = "none";
        refresh();
    }
    function printNow() {
        if (layout.error || !sheets.length || controller.busy) return;
        var o = options();
        close();
        controller.startPrint(o);
    }
    function go(step) { current = Math.max(0, Math.min(sheets.length-1, current+step)); strip.positionViewAtIndex(current, ListView.Contain); }

    onOpened: {
        printerList = controller.printers();
        if (!printerName || !printerList.some(function(p){ return p.name === printerName; }))
            printerName = printerList.length ? printerList[0].name : "__pdf__";
        range = controller.selection.length > 1 ? "selection" : "all";
        current = 0;
        choosePrinter(printerName);
        sheetArea.forceActiveFocus();
    }
    Timer { id: relayout; interval: 60; onTriggered: preview.refresh() }
    onPageSizeChanged: if (opened) relayout.restart()
    onRangeChanged: if (opened) relayout.restart()
    onCustomChanged: if (opened) relayout.restart()
    onOrientationChanged: if (opened) relayout.restart()
    onFitChanged: if (opened) relayout.restart()

    // One printed sheet: white paper, the page placed and turned as it prints.
    component Sheet: Item {
        id: sheet
        property var entry: null
        property real scale: 1
        property string kind: "print"
        property bool showArea: false
        readonly property var paper: preview.layout.paper || [595, 842]
        readonly property var r: entry ? entry.rect : [0, 0, 1, 1]
        property string source: ""
        width: paper[0]*scale; height: paper[1]*scale
        function load() {
            if (!entry) return;
            var pageWidth = (entry.rotate ? r[3] : r[2]) * scale * Screen.devicePixelRatio;
            source = preview.controller.imageUrl(entry.page, kind);
            preview.controller.requestPage(entry.page, kind, Math.ceil(pageWidth));
        }
        onEntryChanged: load()
        onScaleChanged: loadLater.restart()
        Timer { id: loadLater; interval: 120; onTriggered: sheet.load() }
        Connections {
            target: preview.controller
            function onPageImageChanged(page, kind) { if (sheet.entry && page === sheet.entry.page && kind === sheet.kind) sheet.source = preview.controller.imageUrl(page, kind); }
        }
        Rectangle { x: 2; y: 3; width: parent.width; height: parent.height; radius: 2; color: Theme.shadow }
        Rectangle { anchors.fill: parent; color: "white"; border.color: Theme.pageEdge }
        // Printable area of this printer and paper.
        Rectangle {
            visible: sheet.showArea && !!preview.layout.area
            x: (preview.layout.area ? preview.layout.area[0] : 0)*sheet.scale; y: (preview.layout.area ? preview.layout.area[1] : 0)*sheet.scale
            width: (preview.layout.area ? preview.layout.area[2] : 0)*sheet.scale; height: (preview.layout.area ? preview.layout.area[3] : 0)*sheet.scale
            color: "transparent"; border.color: "#1f000000"; border.width: 1
        }
        Item {
            x: sheet.r[0]*sheet.scale; y: sheet.r[1]*sheet.scale
            width: sheet.r[2]*sheet.scale; height: sheet.r[3]*sheet.scale
            clip: true
            layer.enabled: preview.gray
            layer.effect: MultiEffect { saturation: -1 }
            Rectangle { anchors.fill: parent; color: "#f3f4f6"; visible: !pageImage.source.toString().length }
            Image {
                id: pageImage
                anchors.centerIn: parent
                width: sheet.entry && sheet.entry.rotate ? parent.height : parent.width
                height: sheet.entry && sheet.entry.rotate ? parent.width : parent.height
                rotation: sheet.entry && sheet.entry.rotate ? 90 : 0
                source: sheet.source; asynchronous: true; cache: false; smooth: true; mipmap: true
                fillMode: Image.Stretch; retainWhileLoading: true
            }
        }
    }

    contentItem: RowLayout {
        spacing: 0
        // ---- Settings -------------------------------------------------------
        Rectangle {
            Layout.preferredWidth: 330; Layout.fillHeight: true; color: Theme.surface
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.line }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 20; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; text: "인쇄"; font.pixelSize: 20; font.weight: Font.DemiBold; color: Theme.ink; Layout.fillWidth: true }
                    ActionButton { glyph: "close"; compact: true; hint: "닫기 · Esc"; onClicked: preview.close() }
                }
                ScrollView {
                    id: settingsScroll
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: settingsScroll.availableWidth; spacing: 14
                        component Label: Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; font.pixelSize: 13; font.weight: Font.DemiBold; color: Theme.inkSoft }

                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Label { text: "프린터" }
                            ComboBox {
                                objectName: "printPrinter"; Layout.fillWidth: true
                                model: preview.printerList; textRole: "label"; valueRole: "name"
                                currentIndex: { for (var i = 0; i < preview.printerList.length; ++i) if (preview.printerList[i].name === preview.printerName) return i; return -1; }
                                onActivated: preview.choosePrinter(currentValue)
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Label { text: "페이지" }
                            ButtonGroup { id: rangeGroup }
                            RadioButton { objectName: "printRangeAll"; text: "모든 페이지 (" + preview.controller.document.count + "쪽)"; checked: preview.range === "all"; ButtonGroup.group: rangeGroup; onClicked: preview.range = "all" }
                            RadioButton { objectName: "printRangeCurrent"; text: "현재 페이지 (" + (preview.controller.currentPage+1) + "쪽)"; checked: preview.range === "current"; ButtonGroup.group: rangeGroup; onClicked: preview.range = "current" }
                            RadioButton { visible: preview.controller.selection.length > 1; text: "선택한 페이지 (" + preview.controller.selection.length + "쪽)"; checked: preview.range === "selection"; ButtonGroup.group: rangeGroup; onClicked: preview.range = "selection" }
                            RowLayout {
                                Layout.fillWidth: true
                                RadioButton { objectName: "printRangeCustom"; text: "직접 입력"; checked: preview.range === "custom"; ButtonGroup.group: rangeGroup; onClicked: { preview.range = "custom"; customField.forceActiveFocus(); } }
                                TextField {
                                    id: customField; objectName: "printRangeText"; Layout.fillWidth: true
                                    placeholderText: "예: 1-3, 5"; selectByMouse: true; text: preview.custom
                                    onTextEdited: { preview.custom = text; preview.range = "custom"; }
                                    onAccepted: preview.printNow()
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Label { text: "매수" }
                            RowLayout {
                                SpinBox { objectName: "printCopies"; from: 1; to: 999; value: preview.copies; editable: true; onValueModified: preview.copies = value }
                                CheckBox { visible: preview.copies > 1; text: "한 부씩 인쇄"; checked: preview.collate; onToggled: preview.collate = checked }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Label { text: "방향" }
                            Segmented {
                                ActionButton { objectName: "printOrientAuto"; compact: true; segmented: true; text: "자동"; hint: "페이지 모양에 맞춰 용지 방향을 고르고, 다른 모양의 페이지는 돌려서 인쇄"; active: preview.orientation === "auto"; onClicked: preview.orientation = "auto" }
                                ActionButton { compact: true; segmented: true; text: "세로"; active: preview.orientation === "portrait"; onClicked: preview.orientation = "portrait" }
                                ActionButton { compact: true; segmented: true; text: "가로"; active: preview.orientation === "landscape"; onClicked: preview.orientation = "landscape" }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Label { text: "용지" }
                            ComboBox {
                                objectName: "printPaper"; Layout.fillWidth: true
                                model: preview.setup.sizes; textRole: "name"; valueRole: "id"
                                currentIndex: { var s = preview.setup.sizes || []; for (var i = 0; i < s.length; ++i) if (s[i].id === preview.pageSize) return i; return -1; }
                                onActivated: preview.pageSize = currentValue
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Label { text: "크기" }
                            Segmented {
                                ActionButton { objectName: "printFitShrink"; compact: true; segmented: true; text: "큰 페이지만 줄이기"; hint: "용지보다 큰 페이지만 줄이고, 나머지는 원래 크기"; active: preview.fit === "shrink"; onClicked: preview.fit = "shrink" }
                                ActionButton { objectName: "printFitFit"; compact: true; segmented: true; text: "맞춤"; hint: "인쇄 영역에 꽉 차게"; active: preview.fit === "fit"; onClicked: preview.fit = "fit" }
                                ActionButton { objectName: "printFitActual"; compact: true; segmented: true; text: "100%"; hint: "원래 크기 그대로 (넘치는 부분은 잘려요)"; active: preview.fit === "actual"; onClicked: preview.fit = "actual" }
                            }
                        }
                        CheckBox { objectName: "printGray"; text: "흑백으로 인쇄"; checked: preview.gray; onToggled: preview.gray = checked }
                        ColumnLayout {
                            visible: preview.setup.duplex; Layout.fillWidth: true; spacing: 6
                            Label { text: "양면" }
                            ComboBox {
                                Layout.fillWidth: true
                                model: [{ k: "none", t: "단면" }, { k: "long", t: "양면 · 긴 쪽으로 넘김" }, { k: "short", t: "양면 · 짧은 쪽으로 넘김" }]
                                textRole: "t"; valueRole: "k"
                                currentIndex: ["none", "long", "short"].indexOf(preview.duplex)
                                onActivated: preview.duplex = currentValue
                            }
                        }
                        Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
                            Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 13; color: Theme.accentInk
                            text: "프린터 전용 설정(용지함, 품질 등)이 필요하면"
                        }
                        ActionButton {
                            objectName: "printSystemDialog"; outlined: true; text: "프린터 설정 창에서 인쇄…"; Layout.topMargin: -8
                            enabled: !preview.toPdf
                            onClicked: { preview.close(); Qt.callLater(preview.controller.printDocument); }
                        }
                    }
                }
                Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
                    objectName: "printError"; visible: !!preview.layout.error; Layout.fillWidth: true; wrapMode: Text.WordWrap
                    text: preview.layout.error || ""; color: Theme.danger; font.pixelSize: 13
                }
                Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
                    objectName: "printSummary"; Layout.fillWidth: true; font.pixelSize: 13; color: Theme.inkMuted
                    text: preview.sheets.length ? ("용지 " + preview.sheets.length + "장" + (preview.copies > 1 ? " × " + preview.copies + "부" : "") + (preview.gray ? " · 흑백" : "") + (preview.duplex !== "none" ? " · 양면" : "")) : ""
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Item { Layout.fillWidth: true }
                    ActionButton { text: "취소"; onClicked: preview.close() }
                    ActionButton {
                        objectName: "printNowButton"; primary: true; implicitWidth: 104
                        text: preview.toPdf ? "PDF로 저장" : "인쇄"
                        enabled: !preview.layout.error && preview.sheets.length > 0 && !preview.controller.busy
                        onClicked: preview.printNow()
                    }
                }
            }
        }
        // ---- Preview ----------------------------------------------------------
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            RowLayout {
                Layout.fillWidth: true; Layout.margins: 14; spacing: 6
                Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; text: "미리보기"; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.ink }
                Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality;
                    text: preview.currentSheet ? "· " + (preview.currentSheet.page+1) + "쪽" + (preview.currentSheet.rotate ? " (돌려서 인쇄)" : "") : ""
                    font.pixelSize: 14; color: Theme.inkMuted
                }
                Item { Layout.fillWidth: true }
                Segmented {
                    ActionButton { glyph: "left"; compact: true; segmented: true; enabled: preview.current > 0; hint: "이전 장 · ←"; onClicked: preview.go(-1) }
                    ActionButton { objectName: "printSheetLabel"; compact: true; segmented: true; implicitWidth: 76; text: preview.currentSheet ? (preview.current+1) + " / " + preview.sheets.length : "—" }
                    ActionButton { glyph: "right"; compact: true; segmented: true; enabled: preview.current < preview.sheets.length-1; hint: "다음 장 · →"; onClicked: preview.go(1) }
                }
            }
            Item {
                id: sheetArea; objectName: "printSheetArea"
                Layout.fillWidth: true; Layout.fillHeight: true; focus: true
                Keys.onLeftPressed: preview.go(-1)
                Keys.onRightPressed: preview.go(1)
                Keys.onUpPressed: preview.go(-1)
                Keys.onDownPressed: preview.go(1)
                Keys.onReturnPressed: preview.printNow()
                Keys.onEnterPressed: preview.printNow()
                WheelHandler { onWheel: function(event) { preview.go(event.angleDelta.y > 0 ? -1 : 1); } }
                readonly property var paper: preview.layout.paper || [595, 842]
                Sheet {
                    objectName: "printSheet"
                    visible: preview.sheets.length > 0
                    anchors.centerIn: parent
                    entry: preview.currentSheet
                    scale: Math.max(.05, Math.min((sheetArea.width-48)/sheetArea.paper[0], (sheetArea.height-40)/sheetArea.paper[1]))
                    showArea: true
                }
                Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; visible: !preview.sheets.length; anchors.centerIn: parent; text: preview.layout.error ? "페이지 범위를 확인해 주세요." : "인쇄할 페이지가 없어요."; color: Theme.inkMuted; font.pixelSize: 14 }
            }
            ListView {
                id: strip; objectName: "printStrip"
                Layout.fillWidth: true; Layout.preferredHeight: 128; Layout.bottomMargin: 8
                orientation: ListView.Horizontal; spacing: 10; clip: true
                leftMargin: 14; rightMargin: 14
                model: preview.sheets.length
                delegate: Item {
                    id: stripCell; required property int index
                    readonly property var paper: preview.layout.paper || [595, 842]
                    width: thumb.width + 12; height: strip.height
                    Rectangle {
                        anchors.fill: parent; anchors.margins: 1; radius: Theme.radius
                        color: stripCell.index === preview.current ? Theme.accentSoft : thumbMouse.containsMouse ? Theme.hover : "transparent"
                        border.color: stripCell.index === preview.current ? Theme.accent : "transparent"; border.width: 1.5
                    }
                    Sheet {
                        id: thumb; kind: "printThumb"
                        x: 6; y: 6
                        scale: 92/Math.max(stripCell.paper[0], stripCell.paper[1])
                        entry: stripCell.index < preview.sheets.length ? preview.sheets[stripCell.index] : null
                    }
                    Text { renderType: Text.QtRendering; renderTypeQuality: Text.HighRenderTypeQuality; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 4; text: stripCell.index < preview.sheets.length ? (preview.sheets[stripCell.index].page+1) : ""; font.pixelSize: 12; color: stripCell.index === preview.current ? Theme.accentInk : Theme.inkMuted }
                    MouseArea { id: thumbMouse; anchors.fill: parent; hoverEnabled: true; onClicked: { preview.current = stripCell.index; sheetArea.forceActiveFocus(); } }
                }
            }
        }
    }
}
