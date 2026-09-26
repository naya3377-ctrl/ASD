import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "mainWindow"
    width: 1320; height: 900
    minimumWidth: presenting ? 0 : 1000; minimumHeight: presenting ? 0 : 640
    visibility: Window.Windowed
    title: root.hasDocument ? (pdf.document.dirty ? "● " : "") + pdf.document.name + " — 윤DF" : "윤DF"
    color: "#f4f5f2"
    property string uiFontFamily: Qt.platform.os === "windows" ? "Segoe UI Variable" : "Noto Sans CJK KR"
    font.family: uiFontFamily
    font.pixelSize: 14
    contentItem.enabled: !(root.tabWorkspace && root.tabWorkspace.closing)
    property var tabWorkspace: typeof documents !== "undefined" ? documents : null
    property var pdf: tabWorkspace ? tabWorkspace.activeBridge : bridge
    property bool switching: false
    property bool closeAllRequested: false
    function quitApplication() { closeAllRequested=true; close(); }
    property bool restoring: false
    property bool dialogsClear: !textDialog.visible && !annotationEditor.visible && !mergeDialog.visible && !ocrDialog.visible && !settingsDialog.visible && !errorDialog.visible && !aboutDialog.visible && !(tabWorkspace && tabWorkspace.closing)
    property bool tabActionsEnabled: dialogsClear && !presenting
    property bool externalOpenReady: dialogsClear && !readerMenuOpen && !tabMenu.visible && !switching
    property bool externalOpenPending: typeof externalRequests !== "undefined" && externalRequests.pending
    property bool presenting: false
    property var presentationState: null
    property bool readerMenuOpen: false
    property bool typingText: activeFocusItem instanceof TextInput || activeFocusItem instanceof TextEdit
    property bool pageKeysEnabled: hasDocument && !pageViewMode.activeFocus && !pageViewMode.popup.visible && !textDialog.visible && !mergeDialog.visible && !ocrDialog.visible && !settingsDialog.visible && !errorDialog.visible && !aboutDialog.visible && !typingText && !readerMenuOpen && !tabMenu.visible && !switching
    property var pendingNavigation: null
    property string tool: "read"
    property string workspaceMode: "read"
    property real zoom: 1
    property bool twoPageView: false
    property int pageColumns: twoPageView ? 2 : 1
    function rowForPage(page) { return Math.floor(page/pageColumns); }
    function cellForPage(page) {
        var row=pages.itemAtIndex(rowForPage(page));
        return row ? row.pageItem(page%pageColumns) : null;
    }
    function cellTop(cell) { return cell.mapToItem(pages.contentItem,0,0).y; }
    function setTwoPageView(value) {
        if(twoPageView===value) return;
        var page=pdf.currentPage;
        restoring=true; twoPageView=value;
        Qt.callLater(function(){root.goPage(page);});
    }
    property bool sidebarOpen: true
    property bool searchOpen: false
    property bool canAnnotate: pdf.document.annotatable === true && !pdf.busy && !pdf.ocrBusy && !textDialog.visible && !annotationEditor.visible
    onWorkspaceModeChanged: if(pdf) pdf.setAnnotationPanelVisible(workspaceMode==="comments")
    onPdfChanged: { if(presenting) endPresentation(); if(pdf) pdf.setAnnotationPanelVisible(workspaceMode==="comments"); }
    property bool canEdit: pdf.document.editable && !pdf.busy && !pdf.ocrBusy && !textDialog.visible && !annotationEditor.visible
    property bool hasDocument: pdf.document.count > 0
    property int draggedPage: -1
    property var draggedPages: []
    property int dropIndex: -1
    property real dragViewportY: 0
    property string pendingQuery: ""

    function goPage(page) {
        if (!Number.isFinite(page) || page < 0 || page >= pdf.document.count) return;
        navigationTimer.stop(); pendingNavigation=null;
        restoring=!presenting;
        pdf.selectPage(page, false, false);
        if(presenting) return;
        pages.cancelFlick();
        pages.positionViewAtIndex(rowForPage(page), ListView.Beginning);
        pendingNavigation={owner:pdf,page:page,offset:0,horizontal:pages.contentX/Math.max(1,pages.contentWidth),tries:0};
        navigationTimer.restart();
        if (tool === "editText") pdf.loadBlocks(page);
    }
    function turnPage(amount) {
        goPage(Math.max(0,Math.min(pdf.document.count-1,pdf.currentPage+amount*(presenting ? 1 : pageColumns))));
        if(presenting && presentation.item) presentation.item.forceActiveFocus();
        else pages.forceActiveFocus();
    }
    function startPresentation() {
        if(!hasDocument || !dialogsClear || readerMenuOpen || tabMenu.visible || pdf.busy || pdf.ocrBusy || presenting) return;
        var cell=cellForPage(pdf.currentPage);
        presentationState={owner:pdf,page:pdf.currentPage,offset:cell ? (pages.contentY-cellTop(cell))/cell.pageWidth : 0,
            horizontal:pages.contentX/Math.max(1,pages.contentWidth),visibility:visibility,x:x,y:y,width:width,height:height};
        navigationTimer.stop(); pendingNavigation=null; restoring=false;
        searchDelay.stop(); pages.cancelFlick();
        pdf.setPresentationActive(true); pdf.setAnnotationPanelVisible(false);
        presenting=true;
        showFullScreen();
        if(presentation.item) presentation.item.forceActiveFocus();
    }
    function endPresentation() {
        if(!presenting) return;
        var state=presentationState, owner=pdf, page=pdf.currentPage;
        presenting=false; restoring=true;
        if(state && state.owner) state.owner.setPresentationActive(false);
        if(state) {
            visibility=state.visibility;
            if(state.visibility===Window.Windowed) { x=state.x; y=state.y; width=state.width; height=state.height; }
        }
        pdf.setAnnotationPanelVisible(workspaceMode==="comments");
        Qt.callLater(function() {
            if(root.pdf!==owner || root.presenting || root.switching) return;
            pages.forceLayout();
            pages.positionViewAtIndex(rowForPage(page),ListView.Beginning);
            pendingNavigation={owner:owner,page:page,offset:state && state.owner===owner && state.page===page ? state.offset : 0,
                horizontal:state && state.owner===owner ? state.horizontal : 0,tries:0};
            if(root.hasDocument) navigationTimer.restart(); else root.restoring=false;
            pages.forceActiveFocus();
            if(root.tool==="editText" && root.hasDocument && !pdf.busy) pdf.loadBlocks(page);
            if(searchInput.text!==pdf.searchQuery) searchDelay.restart();
        });
    }
    function togglePresentation() { if(presenting) endPresentation(); else startPresentation(); }
    onHasDocumentChanged: if(!hasDocument && presenting) endPresentation()
    onVisibilityChanged: function(state) { if(presenting && state!==Window.FullScreen && state!==Window.Minimized) endPresentation(); }
    function saveView() {
        if (!tabWorkspace) return;
        if(presenting) endPresentation();
        searchDelay.stop(); navigationTimer.stop(); pendingNavigation=null;
        var page=pdf.currentPage, cell=cellForPage(page);
        tabWorkspace.rememberView({page:page,offset:cell ? (pages.contentY-cellTop(cell))/cell.pageWidth : 0,
            x:pages.contentX/Math.max(1,pages.contentWidth),zoom:zoom,twoPage:twoPageView,tool:tool,mode:workspaceMode,
            sidebar:sidebarOpen,search:searchOpen,query:searchInput.text});
        switching=true; restoring=true;
    }
    function restoreView() {
        var state=tabWorkspace.viewState, owner=pdf;
        twoPageView=!!state.twoPage; zoom=state.zoom || 1; tool=state.tool || "read"; workspaceMode=state.mode || "read";
        sidebarOpen=state.sidebar === undefined ? true : state.sidebar; searchOpen=!!state.search;
        searchInput.text=state.query === undefined ? pdf.searchQuery : state.query; pendingQuery=searchInput.text;
        switching=false;
        Qt.callLater(function() {
            if(root.pdf!==owner) return;
            var page=state.page === undefined ? pdf.currentPage : state.page;
            if (pdf.document.count>0) {
                pages.forceLayout(); pages.positionViewAtIndex(rowForPage(page),ListView.Beginning);
                pendingNavigation={owner:pdf,page:page,offset:state.offset || 0,horizontal:state.x || 0,tries:0};
                navigationTimer.restart();
            } else restoring=false;
            if (searchInput.text !== pdf.searchQuery) searchDelay.restart();
        });
    }
    function jumpTo(page,x,y) {
        if(page<0 || page>=pdf.document.count) return;
        if(presenting) { goPage(page); return; }
        restoring=true;
        root.goPage(page); pages.forceLayout();
        pendingNavigation={owner:pdf,page:page,x:x,y:y,tries:0};
        navigationTimer.restart();
    }
    function useTool(value) {
        if(textDialog.visible || annotationEditor.visible) return;
        tool = value;
        if (value==="note") workspaceMode="comments";
        else if (["highlight","underline","strikeout"].indexOf(value)>=0) {}
        else if (["read","hand"].indexOf(value)<0) workspaceMode = "edit";
        if (value === "editText") pdf.loadBlocks(pdf.currentPage);
    }
    onClosing: function(event) {
        if(annotationEditor.visible || textDialog.visible) {
            event.accepted=false; draftClose.open(); return;
        }
        if(externalOpenPending) {
            event.accepted=false; closeAllRequested=false; return;
        }
        if(tabWorkspace && !closeAllRequested && tabStrip.count>1) {
            event.accepted=false;
            tabWorkspace.closeTab(tabWorkspace.activeIndex);
            return;
        }
        event.accepted=tabWorkspace ? tabWorkspace.mayClose() : pdf.mayClose();
        closeAllRequested=false;
    }

    Shortcut { sequence: "Escape"; enabled: (textDialog.visible || annotationEditor.visible) && !pdf.busy && !errorDialog.visible && !fontChoice.popupOpen && !draftClose.visible; onActivated: { if(textDialog.visible) textDialog.close(); else annotationEditor.close(); } }
    Shortcut { sequence: "Ctrl+Shift+Q"; enabled: !pdf.busy && !draftClose.visible; onActivated: root.quitApplication() }
    Shortcut { sequence: "Ctrl+Tab"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.cycle(1) }
    Shortcut { sequence: "Ctrl+Shift+Tab"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.cycle(-1) }
    Shortcut { sequence: "Ctrl+W"; enabled: !!root.tabWorkspace && !pdf.busy && !draftClose.visible; onActivated: {if(textDialog.visible || annotationEditor.visible)root.close();else root.tabWorkspace.closeTab(root.tabWorkspace.activeIndex);} }
    Shortcut { sequence: "Ctrl+T"; enabled: !!root.tabWorkspace && root.tabActionsEnabled; onActivated: root.tabWorkspace.newTab() }
    Shortcut { sequence: "F3"; enabled: root.hasDocument && root.tabActionsEnabled; onActivated: pdf.findNext(searchInput.text,1) }
    Shortcut { sequence: "Shift+F3"; enabled: root.hasDocument && root.tabActionsEnabled; onActivated: pdf.findNext(searchInput.text,-1) }
    Shortcut { sequences: ["F5","F11","Ctrl+L"]; autoRepeat: false; enabled: root.hasDocument && root.dialogsClear; onActivated: root.togglePresentation() }
    Shortcut { sequences: ["Right","Down","PgDown","Space"]; enabled: root.pageKeysEnabled; onActivated: root.turnPage(1) }
    Shortcut { sequences: ["Left","Up","PgUp","Shift+Space"]; enabled: root.pageKeysEnabled; onActivated: root.turnPage(-1) }
    Shortcut { sequences: ["Home","Ctrl+Home"]; enabled: root.pageKeysEnabled; onActivated: root.goPage(0) }
    Shortcut { sequences: ["End","Ctrl+End"]; enabled: root.pageKeysEnabled; onActivated: root.goPage(pdf.document.count-1) }
    Shortcut { sequence: StandardKey.Open; enabled: root.tabActionsEnabled; onActivated: pdf.chooseOpen() }
    Shortcut { sequence: StandardKey.Print; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onActivated: pdf.printDocument() }
    Shortcut { sequence: StandardKey.SelectAll; enabled: root.tabActionsEnabled && root.tool === "read" && !root.typingText; onActivated: pdf.selectAllText() }
    Shortcut { sequence: StandardKey.Save; enabled: root.tabActionsEnabled; onActivated: pdf.save(false) }
    Shortcut { sequence: StandardKey.SaveAs; enabled: root.tabActionsEnabled; onActivated: pdf.save(true) }
    Shortcut { sequences: [StandardKey.Undo]; enabled: root.tabActionsEnabled && (root.canEdit || root.canAnnotate) && pdf.document.canUndo; onActivated: pdf.undo() }
    Shortcut { sequences: [StandardKey.Redo]; enabled: root.tabActionsEnabled && (root.canEdit || root.canAnnotate) && pdf.document.canRedo; onActivated: pdf.redo() }
    Shortcut { sequence: StandardKey.Find; enabled: root.tabActionsEnabled; onActivated: { root.searchOpen = true; root.sidebarOpen = true; searchInput.forceActiveFocus(); } }
    Shortcut { sequences: [StandardKey.Copy]; enabled: root.tabActionsEnabled && !root.typingText; onActivated: pdf.copySelection() }
    Shortcut { sequence: "Ctrl++"; enabled: root.tabActionsEnabled; onActivated: root.zoom = Math.min(3, root.zoom + .15) }
    Shortcut { sequence: "Ctrl+-"; enabled: root.tabActionsEnabled; onActivated: root.zoom = Math.max(.3, root.zoom - .15) }
    Shortcut { sequence: "Ctrl+0"; enabled: root.tabActionsEnabled; onActivated: root.zoom = 1 }
    Shortcut { sequence: "Escape"; enabled: root.dialogsClear && !root.readerMenuOpen && !tabMenu.visible; onActivated: { if(root.presenting) root.endPresentation(); else root.useTool("read"); } }
    Shortcut { sequence: "Ctrl+Shift+R"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.rotateSelected() }
    Shortcut { sequence: "Alt+Up"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.moveSelected(-1) }
    Shortcut { sequence: "Alt+Down"; enabled: root.canEdit && root.tabActionsEnabled; onActivated: pdf.moveSelected(1) }

    header: ColumnLayout {
        objectName: "readerHeader"; visible: !root.presenting
        enabled: !(root.tabWorkspace && root.tabWorkspace.closing)
        spacing: 0
        Rectangle {
            Layout.fillWidth: true; height: 62; color: "#fdfefc"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 8
                Image { source: "../assets/icon.svg"; Layout.preferredWidth: 30; Layout.preferredHeight: 30 }
                Text { text: "윤DF"; font.pixelSize: 16; font.weight: Font.DemiBold; color: "#263b32"; Layout.rightMargin: 18 }
                ActionButton { glyph: "open"; text: "열기"; hint: "Ctrl+O"; enabled: root.tabActionsEnabled && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.chooseOpen() }
                ActionButton { objectName: "mergeButton"; glyph: "merge"; text: "PDF 결합"; enabled: root.tabActionsEnabled && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.showMerge() }
                Rectangle { width: 1; height: 22; color: "#e3e8e1"; Layout.leftMargin: 8; Layout.rightMargin: 8 }
                Text { text: root.hasDocument ? pdf.document.name : "문서를 위한 조용한 작업 공간"; font.pixelSize: 13; color: root.hasDocument ? "#435347" : "#9aa499"; elide: Text.ElideMiddle; Layout.fillWidth: true }
                Rectangle { visible: pdf.document.dirty; width: 6; height: 6; radius: 3; color: "#8d9a72"; Layout.rightMargin: 12 }
                ActionButton { objectName: "presentationButton"; glyph: "present"; text: "슬라이드 쇼"; hint: "전체 화면 · F5 / F11 / Ctrl+L"; enabled: root.hasDocument && !pdf.busy && !pdf.ocrBusy; onClicked: root.startPresentation() }
                ActionButton { glyph: "search"; hint: "문서 검색 · Ctrl+F"; active: root.searchOpen; enabled: root.hasDocument; onClicked: { root.searchOpen=!root.searchOpen; root.sidebarOpen=true; if(root.searchOpen) searchInput.forceActiveFocus(); } }
                ActionButton { objectName: "printButton"; glyph: "print"; hint: "인쇄 · Ctrl+P"; enabled: root.tabActionsEnabled && root.hasDocument && pdf.document.printable && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.printDocument() }
                ActionButton { glyph: "save-as"; hint: "다른 이름으로 저장"; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.save(true) }
                ActionButton { text: "저장"; primary: true; implicitWidth: 70; enabled: root.tabActionsEnabled && root.hasDocument && !pdf.busy && !pdf.ocrBusy; onClicked: pdf.save(false) }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e1e6df" }
        }
        Rectangle {
            visible: !!root.tabWorkspace
            Layout.fillWidth: true; height: 44; color: "#eaf0e9"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 6
                ListView {
                    id: tabStrip; objectName: "documentTabs"; Layout.fillWidth: true; Layout.fillHeight: true
                    orientation: ListView.Horizontal; spacing: 5; clip: true
                    model: root.tabWorkspace ? root.tabWorkspace.tabModel : null
                    function syncIndex() {
                        currentIndex=root.tabWorkspace ? root.tabWorkspace.activeIndex : 0;
                        positionViewAtIndex(currentIndex,ListView.Contain);
                    }
                    Connections { target: root.tabWorkspace; function onIndexChanged() { tabStrip.syncIndex(); } }
                    Component.onCompleted: syncIndex()
                    onCurrentIndexChanged: positionViewAtIndex(currentIndex,ListView.Contain)
                    onCountChanged: Qt.callLater(syncIndex)
                    delegate: Rectangle {
                        id: documentTab; required property var modelData; required property int index
                        objectName: "documentTab"+index
                        y: 5; height: 39; width: Math.min(240,Math.max(172,tabTitle.implicitWidth+66))
                        radius: 7; color: index===root.tabWorkspace.activeIndex ? "#fcfdfb" : tabMouse.containsMouse ? "#f2f5f0" : "transparent"
                        border.color: index===root.tabWorkspace.activeIndex ? "#d7e1d5" : "transparent"
                        MouseArea {
                            id: tabMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                            enabled: root.tabActionsEnabled
                            onClicked: function(event){ if(event.button===Qt.MiddleButton) root.tabWorkspace.closeId(documentTab.modelData.id); else root.tabWorkspace.activateId(documentTab.modelData.id); }
                        }
                        ToolTip.visible: tabMouse.containsMouse; ToolTip.delay: 700; ToolTip.text: modelData.path || "새 문서"
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 5; spacing: 7
                            Rectangle { width: 5; height: 5; radius: 3; color: modelData.dirty ? "#ad8145" : modelData.busy ? "#618478" : "transparent" }
                            Text { id: tabTitle; text: documentTab.modelData.name; Layout.fillWidth: true; elide: Text.ElideMiddle; color: documentTab.index===root.tabWorkspace.activeIndex ? "#294639" : "#72816f"; font.pixelSize: 12; font.weight: documentTab.index===root.tabWorkspace.activeIndex ? Font.DemiBold : Font.Normal }
                            ActionButton { objectName: "closeTab"+documentTab.index; glyph: "close"; implicitWidth: 26; implicitHeight: 27; hint: "탭 닫기 · Ctrl+W"; enabled: root.tabActionsEnabled; onClicked: root.tabWorkspace.closeId(documentTab.modelData.id) }
                        }
                        Rectangle { anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; width: parent.width-22; height: 2; color: "#4b7560"; visible: documentTab.index===root.tabWorkspace.activeIndex }
                    }
                }
                ActionButton { glyph: "add"; hint: "새 탭 · Ctrl+T"; implicitWidth: 30; enabled: root.tabActionsEnabled; onClicked: root.tabWorkspace.newTab() }
                ActionButton { objectName: "openDocumentsButton"; glyph: "down"; hint: "열린 문서 목록"; implicitWidth: 30; enabled: root.tabActionsEnabled; onClicked: tabMenu.popup() }
            }
            Menu {
                id: tabMenu; objectName: "openDocumentsMenu"
                Repeater {
                    model: root.tabWorkspace ? root.tabWorkspace.tabModel : null
                    MenuItem { required property var modelData; required property int index; text: (modelData.dirty ? "● " : "")+modelData.name; checkable: true; checked: index===root.tabWorkspace.activeIndex; onTriggered: root.tabWorkspace.activateId(modelData.id) }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true; height: 54; color: "#f6f8f4"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 7
                ActionButton { glyph: "sidebar"; hint: "페이지 미리보기"; active: root.sidebarOpen; onClicked: root.sidebarOpen=!root.sidebarOpen }
                Rectangle { width: 1; height: 20; color: "#e0e6dc"; Layout.leftMargin: 6; Layout.rightMargin: 10 }
                ActionButton { objectName: "readModeButton"; enabled: !textDialog.visible && !annotationEditor.visible; text: "읽기"; active: root.workspaceMode === "read"; onClicked: { root.workspaceMode="read"; root.useTool("read"); } }
                ActionButton { objectName: "editModeButton"; text: "편집"; active: root.workspaceMode === "edit"; enabled: root.hasDocument && !textDialog.visible && !annotationEditor.visible; onClicked: { root.workspaceMode="edit"; root.useTool("editText"); } }
                ActionButton { objectName: "commentsModeButton"; text: "주석"; active: root.workspaceMode==="comments"; enabled: root.hasDocument && !textDialog.visible && !annotationEditor.visible; onClicked: { root.workspaceMode="comments"; root.useTool("read"); } }
                ActionButton { text: "페이지 정리"; active: root.workspaceMode === "pages"; enabled: root.hasDocument && !textDialog.visible && !annotationEditor.visible; onClicked: { root.workspaceMode="pages"; root.sidebarOpen=true; root.useTool("read"); } }
                Item { Layout.fillWidth: true }
                ActionButton { visible: root.workspaceMode !== "edit"; glyph: "text"; hint: "텍스트 선택"; active: root.tool === "read"; enabled: root.hasDocument; onClicked: root.useTool("read") }
                ActionButton { visible: root.workspaceMode !== "edit"; glyph: "hand"; hint: "손 도구"; active: root.tool === "hand"; enabled: root.hasDocument; onClicked: root.useTool("hand") }
                Rectangle { width: 1; height: 20; color: "#e0e6dc"; Layout.leftMargin: 8; Layout.rightMargin: 8 }
                ComboBox {
                    id: pageViewMode; objectName: "pageViewMode"; implicitWidth: 116; model: ["한 페이지", "두 페이지"]
                    enabled: root.hasDocument && !textDialog.visible; currentIndex: root.twoPageView ? 1 : 0
                    font.pixelSize: 13
                    background: Rectangle { radius: 7; color: pageViewMode.hovered ? "#edf0ee" : "#fcfdfb"; border.color: "#dce2df" }
                    indicator: Image { source: "../assets/icons/down.svg"; width: 16; height: 16; x: parent.width-width-10; y: (parent.height-height)/2 }
                    onActivated: root.setTwoPageView(currentIndex===1)
                }
                ActionButton { glyph: "minus"; hint: "축소"; enabled: root.hasDocument; onClicked: root.zoom=Math.max(.3,root.zoom-.15) }
                ActionButton { text: Math.round(root.zoom*100)+"%"; hint: "너비 맞춤 · Ctrl+0"; enabled: root.hasDocument; implicitWidth: 60; onClicked: root.zoom=1 }
                ActionButton { glyph: "add"; hint: "확대"; enabled: root.hasDocument; onClicked: root.zoom=Math.min(3,root.zoom+.15) }
                Rectangle { width: 1; height: 20; color: "#e0e6dc"; Layout.leftMargin: 8; Layout.rightMargin: 8 }
                ActionButton { glyph: "ocr"; text: "문자 인식"; enabled: root.canEdit; onClicked: { pdf.inspectOcr(); ocrDialog.open(); } }
                ActionButton { objectName: "settingsButton"; glyph: "settings"; hint: "설정"; onClicked: settingsDialog.open() }
            }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e0e5dd" }
        }
        Rectangle {
            visible: textDialog.visible; Layout.fillWidth: true; height: visible ? 50 : 0; color: "#edf4ef"
            RowLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 8
                Text { text: "본문에서 편집"; color: "#2f5142"; font.weight: Font.DemiBold }
                FontPicker { id: fontChoice; controller: root.pdf; Layout.fillWidth: true; Layout.maximumWidth: 320; enabled: !pdf.busy }
                ActionButton { text: "글꼴 파일"; enabled: !pdf.busy; onClicked: pdf.chooseFont() }
                TextField { id: sizeInput; objectName: "fontSizeInput"; Layout.preferredWidth: 62; text: textDialog.fontSize.toFixed(2); validator: DoubleValidator { bottom:4; top:200 } selectByMouse: true; onTextEdited: if(acceptableInput) {textDialog.fontSize=Number(text);pdf.liveEditor.setSize(Number(text));} }
                Text { text: "pt"; color: "#718176" }
                Text { text: textDialog.targetData.mode==="replace" ? "자동 줄바꿈" : "높이"; color: "#718176" }
                TextField { visible: textDialog.targetData.mode!=="replace"; objectName: "inlineHeightInput"; Layout.preferredWidth: 62; text: textDialog.areaHeight.toFixed(0); validator: DoubleValidator { bottom:5; top:20000 } selectByMouse: true; onTextEdited: if(acceptableInput) textDialog.areaHeight=Number(text) }
                Item { Layout.fillWidth: true }
                ActionButton { objectName: "cancelTextButton"; text: "취소"; enabled: !pdf.busy; onClicked: {root.closeAfterEdit=false;textDialog.close();} }
                ActionButton { objectName: "applyTextButton"; text: "적용"; primary: true; enabled: !pdf.busy && (textDialog.targetData.mode!=="replace" || pdf.liveEditor.canApply); onClicked: pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight) }
            }
        }
        Rectangle {
            visible: textDialog.visible && textDialog.targetData.mode==="replace" && pdf.liveEditor.status.length>0
            Layout.fillWidth: true; height: visible ? statusLabel.implicitHeight+16 : 0; color: "#fff4dd"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 10
                Text { id: statusLabel; objectName: "inlineFontStatus"; Layout.fillWidth: true; text: pdf.liveEditor.status; wrapMode: Text.WordWrap; color: "#825d2e"; font.pixelSize: 13 }
                ActionButton { objectName: "useMissingFont"; visible: pdf.liveEditor.canUseFallback; text: "없는 글자만 대체"; implicitHeight: 28; onClicked: pdf.liveEditor.useFallback() }
                ActionButton { objectName: "retryFont"; visible: !pdf.liveEditor.loading && !pdf.liveEditor.canApply; text: "다시 시도"; implicitHeight: 28; onClicked: pdf.liveEditor.retry() }
            }
        }
        Rectangle {
            visible: root.hasDocument && ((root.tool !== "read" && root.tool !== "hand") || pdf.pageTextState === "empty" || pdf.pageTextState === "restricted")
            Layout.fillWidth: true; height: visible ? 33 : 0; color: "#edf2e9"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 22; anchors.rightMargin: 15
                Text {
                    Layout.fillWidth: true; font.pixelSize: 12; color: "#708065"; elide: Text.ElideRight
                    text: root.tool === "editText" ? "본문을 클릭해서 그 자리에서 수정하세요. 위쪽 도구 막대에서 적용하거나 취소할 수 있어요." : root.tool === "imageMove" ? "이미지를 드래그해 이동하고, 오른쪽 아래 모서리로 크기를 조절하세요." : ["highlight","underline","strikeout"].indexOf(root.tool)>=0 ? "주석을 남길 글자를 드래그하세요." : root.tool==="note" ? "페이지에서 메모를 남길 위치를 클릭하세요." : ["addText","image"].indexOf(root.tool)>=0 ? "페이지 위에서 편집할 영역을 드래그하세요." : pdf.pageTextState === "restricted" ? "문서 작성자가 텍스트 복사를 제한했어요." : pdf.ocrBusy ? "스캔의 글자를 인식하고 있어요. 문서는 계속 읽을 수 있습니다." : "이 페이지에는 선택할 문자층이 없어요. OCR로 글자를 인식할 수 있습니다."
                }
                ActionButton { visible: pdf.pageTextState === "empty" && !pdf.ocrBusy; implicitHeight: 27; text: "이 페이지 OCR"; enabled: root.canEdit; onClicked: pdf.recognizeCurrentPage() }
            }
        }
    }

    RowLayout {
        objectName: "readerWorkspace"; visible: !root.presenting
        anchors.fill: parent; spacing: 0
        Rectangle {
            visible: root.sidebarOpen
            Layout.preferredWidth: 214; Layout.fillHeight: true; color: "#f8faf6"
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                RowLayout {
                    Layout.fillWidth: true; Layout.margins: 13; spacing: 5
                    Text { text: root.searchOpen ? "문서 검색" : "페이지"; font.weight: Font.DemiBold; font.pixelSize: 14; color: "#343941"; Layout.fillWidth: true }
                    Text { text: pdf.selection.length > 1 ? pdf.selection.length + "개 선택" : root.hasDocument ? (pdf.currentPage+1) + " / " + pdf.document.count : ""; color: "#858b96"; font.pixelSize: 12 }
                }
                ColumnLayout {
                    visible: root.searchOpen; Layout.fillWidth: true; Layout.leftMargin: 12; Layout.rightMargin: 12; spacing: 9
                    TextField {
                        id: searchInput; objectName: "searchInput"; Layout.fillWidth: true
                        placeholderText: "문서에서 찾기"; selectByMouse: true; font.pixelSize: 14
                        leftPadding: 10; rightPadding: 10; color: "#294639"; selectionColor: "#cbdccf"; selectedTextColor: "#1b3628"
                        background: Rectangle { radius: 6; color: "#ffffff"; border.width: searchInput.activeFocus ? 2 : 1; border.color: searchInput.activeFocus ? "#71917c" : "#d7e0d4" }
                        onTextEdited: { root.pendingQuery = text; searchDelay.restart(); }
                        onAccepted: { searchDelay.stop(); pdf.findNext(text,1); }
                        Keys.onPressed: function(event) {
                            if((event.key===Qt.Key_Return || event.key===Qt.Key_Enter) && (event.modifiers & Qt.ShiftModifier)) {
                                searchDelay.stop(); pdf.findNext(text,-1); event.accepted=true;
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { Layout.fillWidth: true; text: pdf.searchCount ? (pdf.searchIndex+1)+" / "+pdf.searchCount+(pdf.searching ? " · 검색 중" : "곳") : pdf.searching ? "검색 중…" : pdf.searchQuery ? "검색 결과 없음" : "검색어를 입력하세요"; color: "#737b87"; font.pixelSize: 12 }
                        ActionButton { objectName: "previousSearchHit"; glyph: "up"; implicitWidth: 28; implicitHeight: 28; hint: "이전 결과 · Shift+Enter"; enabled: pdf.searchCount>0; onClicked: pdf.findNext(searchInput.text,-1) }
                        ActionButton { objectName: "nextSearchHit"; glyph: "down"; implicitWidth: 28; implicitHeight: 28; hint: "다음 결과 · Enter / F3"; enabled: pdf.searchCount>0; onClicked: pdf.findNext(searchInput.text,1) }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.preferredHeight: Math.min(180, contentHeight); clip: true
                        model: pdf.searchResults
                        delegate: ItemDelegate {
                            required property var modelData
                            width: ListView.view.width; height: 35
                            objectName: "searchResult"+modelData.page
                            text: (modelData.page+1) + "페이지  ·  " + modelData.count + "곳"
                            highlighted: pdf.activeSearchHit.page === modelData.page
                            onClicked: pdf.selectSearchHit(modelData.firstHit)
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#dedfe6"; Layout.bottomMargin: 8 }
                }
                ListView {
                    id: thumbs; objectName: "thumbnailList"
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    model: root.switching ? 0 : pdf.document.count; spacing: 12; topMargin: 4; bottomMargin: 16
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Item {
                        id: thumbCell
                        required property int index
                        width: thumbs.width; height: 188
                        property bool selected: pdf.selection.indexOf(index) >= 0
                        property bool near: !root.presenting && y+height >= thumbs.contentY-150 && y <= thumbs.contentY+thumbs.height+150
                        property string pageImage: ""
                        property string renderError: ""
                        property real pageRatio: pdf.pageRatio(index)
                        function request() {
                            pageImage=pdf.imageUrl(index,"thumb");renderError=pdf.imageError(index,"thumb");pageRatio=pdf.pageRatio(index);
                            if (near) pdf.requestPage(index,"thumb",Math.ceil(144*Screen.devicePixelRatio));
                            else pdf.releasePage(index,"thumb");
                        }
                        onNearChanged: request()
                        Component.onCompleted: request()
                        Connections {
                            target: root.pdf
                            function onStateChanged() { thumbCell.request(); }
                            function onPageImageChanged(page,kind) { if(page===thumbCell.index && kind==="thumb") { thumbCell.pageImage=pdf.imageUrl(page,kind);thumbCell.renderError=pdf.imageError(page,kind); } }
                            function onPageMetricsChanged(page) { if(page===thumbCell.index) thumbCell.pageRatio=pdf.pageRatio(page); }
                        }
                        Timer { interval: 700; repeat: true; running: thumbCell.near && !thumbCell.pageImage && !thumbCell.renderError; onTriggered: thumbCell.request() }
                        Rectangle {
                            id: thumbVisual
                            anchors.horizontalCenter: parent.horizontalCenter; y: 2; width: 164; height: 163; radius: 9
                            color: thumbCell.selected ? "#e8eee5" : "transparent"
                            border.color: thumbCell.selected ? "#a5b49e" : "transparent"; border.width: 1
                            Rectangle {
                                objectName: "thumbnailPaper"+thumbCell.index
                                anchors.centerIn: parent; width: Math.min(138,145/thumbCell.pageRatio); height: width*thumbCell.pageRatio
                                color: "white"; border.color: "#d6ddd2"
                                Image { objectName: "thumbnailImage"+thumbCell.index; anchors.fill: parent; anchors.margins: 1; source: thumbCell.pageImage; fillMode: Image.Stretch; cache: false; asynchronous: true; retainWhileLoading: true; smooth: true }
                                BusyIndicator { anchors.centerIn: parent; width: 20; height: 20; running: !thumbCell.pageImage && !thumbCell.renderError; visible: running }
                                ActionButton { anchors.centerIn: parent; visible: !thumbCell.pageImage && !!thumbCell.renderError; text: "재시도"; hint: thumbCell.renderError; onClicked: pdf.retryPage(thumbCell.index,"thumb",Math.ceil(144*Screen.devicePixelRatio)) }
                            }
                            Rectangle { visible: pdf.currentPage===thumbCell.index; x: 6; y: parent.height/2-12; width: 3; height: 24; radius: 2; color: "#48715a"
                            }
                            Drag.active: dragHandler.active
                            Drag.source: thumbCell
                            Drag.hotSpot.x: 70; Drag.hotSpot.y: 80
                            opacity: dragHandler.active ? .6 : 1
                            Text { visible: dragHandler.active; anchors.top: parent.top; anchors.right: parent.right; text: root.draggedPages.length+"장 이동"; color: "#234e3b"; font.bold: true; z: 10 }
                            DragHandler {
                                id: dragHandler; target: null; enabled: root.canEdit
                                onActiveChanged: {
                                    if (active) { if(pdf.selection.indexOf(thumbCell.index)<0) pdf.selectPage(thumbCell.index,false,false); root.draggedPages=pdf.selection.slice(); root.draggedPage = thumbCell.index; root.dropIndex = -1; }
                                    else {
                                        if (root.draggedPage >= 0 && root.dropIndex >= 0) pdf.moveSelectionTo(root.dropIndex);
                                        root.draggedPage = -1; root.dropIndex = -1; root.draggedPages=[];
                                    }
                                }
                                onCentroidChanged: {
                                    if (!active) return;
                                    var p = thumbVisual.mapToItem(thumbs.contentItem, centroid.position.x, centroid.position.y);
                                    root.dragViewportY = thumbVisual.mapToItem(thumbs, centroid.position.x, centroid.position.y).y;
                                    var targetIndex = thumbs.indexAt(thumbs.width/2, p.y);
                                    if (targetIndex >= 0) { var cell=thumbs.itemAtIndex(targetIndex); root.dropIndex=targetIndex+(cell && p.y>cell.y+cell.height/2 ? 1 : 0); } else if(p.y>=thumbs.contentHeight+thumbs.originY) root.dropIndex=pdf.document.count;
                                }
                            }
                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: function(eventPoint) {
                                    pdf.selectPointer(thumbCell.index);
                                    pages.positionViewAtIndex(root.rowForPage(thumbCell.index), ListView.Beginning);
                                    pages.forceActiveFocus();
                                    if (root.tool === "editText") pdf.loadBlocks(thumbCell.index);
                                }
                            }
                        }
                        Rectangle { visible: root.dropIndex === thumbCell.index || (thumbCell.index===pdf.document.count-1 && root.dropIndex===pdf.document.count); x: 26; y: root.dropIndex===pdf.document.count ? parent.height-2 : 0; width: parent.width-52; height: 3; color: "#51765a"; radius: 2 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 172; text: thumbCell.index+1; font.pixelSize: 12; color: thumbCell.selected ? "#436449" : "#899181"; font.weight: thumbCell.selected ? Font.DemiBold : Font.Normal }
                    }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#e0e6d9" }
                ColumnLayout {
                    Layout.fillWidth: true; Layout.margins: 9; spacing: 2
                    RowLayout {
                        spacing: 2; Layout.alignment: Qt.AlignHCenter
                        ActionButton { glyph: "up"; text: ""; hint: "위로 · Alt+↑"; enabled: root.canEdit; onClicked: pdf.moveSelected(-1) }
                        ActionButton { glyph: "down"; text: ""; hint: "아래로 · Alt+↓"; enabled: root.canEdit; onClicked: pdf.moveSelected(1) }
                        ActionButton { glyph: "rotate"; text: ""; hint: "회전"; enabled: root.canEdit; onClicked: pdf.rotateSelected() }
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter; spacing: 4
                        ActionButton { glyph: "add"; text: "PDF 삽입"; enabled: root.canEdit; onClicked: pdf.insertPdf() }
                        ActionButton { glyph: "delete"; text: "삭제"; enabled: root.canEdit; onClicked: pdf.deleteSelected() }
                    }
                }
            }
            Rectangle { anchors.right: parent.right; height: parent.height; width: 1; color: "#e0e5db" }
        }

        Rectangle {
            id: workspace; Layout.fillWidth: true; Layout.fillHeight: true; color: root.hasDocument ? "#e7eae4" : "#f2f5ef"
            TapHandler { onPressedChanged: if(pressed) pages.forceActiveFocus() }
            ListView {
                id: pages; objectName: "pageList"; anchors.fill: parent; clip: true
                visible: root.hasDocument
                model: root.switching ? 0 : Math.ceil(pdf.document.count/root.pageColumns); spacing: 18; topMargin: 24; bottomMargin: 24
                cacheBuffer: Math.max(1200,height*2)
                contentWidth: Math.max(width, (width-64)*root.zoom+64)
                flickableDirection: Flickable.AutoFlickDirection
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                ScrollBar.horizontal: ScrollBar { }
                onContentYChanged: {
                    var idx = indexAt(contentWidth/2, contentY+height*.33);
                    if (idx >= 0 && !root.switching && !root.restoring && !root.presenting) { var first=idx*root.pageColumns; if(pdf.currentPage<first || pdf.currentPage>=first+root.pageColumns) pdf.setCurrentPage(first); }
                }
                delegate: Item {
                    id: spreadRow
                    required property int index
                    width: pages.contentWidth
                    height: spreadPages.childrenRect.height
                    function pageItem(column) { return spreadRepeater.itemAt(column); }
                    Row {
                        id: spreadPages; anchors.horizontalCenter: parent.horizontalCenter; spacing: 16
                        Repeater {
                            id: spreadRepeater
                            model: Math.min(root.pageColumns,pdf.document.count-spreadRow.index*root.pageColumns)
                            delegate: DocumentPage {
                                required property int modelData
                                index: spreadRow.index*root.pageColumns+modelData
                            }
                        }
                    }
                }
            }
            ScrollInput {
                controller: root.pdf
                objectName: "pageScrollInput"; anchors.fill: parent; view: pages; visible: root.hasDocument
                onZoomRequested: function(amount) { root.zoom = Math.max(.3, Math.min(3,root.zoom*amount)); }
            }
            ColumnLayout {
                visible: !root.hasDocument; anchors.centerIn: parent; width: 500; spacing: 18
                Image { source: "../assets/icon.svg"; Layout.preferredWidth: 68; Layout.preferredHeight: 68; Layout.alignment: Qt.AlignHCenter; Layout.bottomMargin: 12 }
                Text { text: "읽고, 다듬고, 하나로."; Layout.alignment: Qt.AlignHCenter; font.pixelSize: 30; font.weight: Font.DemiBold; color: "#314434" }
                Text { text: "필요한 도구만 가까이. 문서에 집중하는 시간."; Layout.alignment: Qt.AlignHCenter; font.pixelSize: 14; color: "#8b9684" }
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter; spacing: 12; Layout.topMargin: 20
                    ActionButton { text: "PDF 열기"; primary: true; implicitWidth: 132; implicitHeight: 43; enabled: !pdf.busy; onClicked: pdf.chooseOpen() }
                    ActionButton { glyph: "merge"; text: "PDF 결합"; outlined: true; implicitWidth: 140; implicitHeight: 43; enabled: !pdf.busy; onClicked: pdf.showMerge() }
                }
                Text { text: "PDF를 이곳에 끌어 놓아도 열 수 있어요."; Layout.alignment: Qt.AlignHCenter; Layout.topMargin: 12; font.pixelSize: 12; color: "#a0a99a" }
            }
            DropArea {
                enabled: root.tabActionsEnabled
                anchors.fill: parent
                onDropped: function(drop) { if (drop.hasUrls) { if(root.tabWorkspace) root.tabWorkspace.openPaths(drop.urls); else if(drop.urls.length) pdf.openPath(drop.urls[0]); } }
            }
        }
        ColumnLayout {
            id: commentsDock; objectName: "commentsDock"
            visible: (root.workspaceMode==="comments" || annotationEditor.visible) && root.hasDocument
            Layout.preferredWidth: 350; Layout.minimumWidth: 300; Layout.maximumWidth: 350; Layout.fillWidth: false; Layout.fillHeight: true; spacing: 0
            AnnotationEditor {
                id: annotationEditor; controller: root.pdf
                Layout.fillWidth: true; Layout.preferredHeight: Math.min(380,commentsDock.height*.63)
                Layout.leftMargin: 16; Layout.rightMargin: 16; Layout.topMargin: visible ? 16 : 0
            }
            CommentsPanel {
                controller: root.pdf; activeTool: root.tool; allowActions: !annotationEditor.visible && !textDialog.visible
                Layout.fillWidth: true; Layout.fillHeight: true
                onToolRequested: function(tool) { if(tool==="closeComments") { root.workspaceMode="read"; root.useTool("read"); } else root.useTool(tool); }
            }
        }
        Rectangle {
            visible: root.workspaceMode === "edit" && root.hasDocument
            Layout.preferredWidth: 218; Layout.fillHeight: true; color: "#fbfcf9"
            Rectangle { width: 1; height: parent.height; color: "#e0e6d9" }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 7
                Text { text: "편집 도구"; font.pixelSize: 16; font.weight: Font.DemiBold; color: "#344532"; Layout.bottomMargin: 12 }
                Text { text: "내용"; font.pixelSize: 11; color: "#919d86" }
                ActionButton { objectName: "editTextButton"; Layout.fillWidth: true; leftAligned: true; glyph: "edit"; text: "본문 수정"; active: root.tool === "editText"; enabled: root.canEdit; onClicked: root.useTool("editText") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "text"; text: "텍스트 추가"; active: root.tool === "addText"; enabled: root.canEdit; onClicked: root.useTool("addText") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "image"; objectName: "insertImageButton"; text: "이미지 삽입"; active: false; enabled: root.canEdit; onClicked: { root.useTool("imageMove"); pdf.chooseImage(); } }
                ActionButton { objectName: "moveImageButton"; Layout.fillWidth: true; leftAligned: true; glyph: "hand"; text: "이미지 이동·크기"; active: root.tool==="imageMove"; enabled: root.canEdit; onClicked: root.useTool("imageMove") }
                Text { text: "주석"; font.pixelSize: 11; color: "#919d86"; Layout.topMargin: 18 }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "highlight"; text: "형광펜"; active: root.tool === "highlight"; enabled: root.canAnnotate; onClicked: root.useTool("highlight") }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "note"; text: "메모"; active: root.tool === "note"; enabled: root.canAnnotate; onClicked: root.useTool("note") }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#e8ede2"; Layout.topMargin: 15; Layout.bottomMargin: 10 }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "undo"; text: "되돌리기"; hint: "Ctrl+Z"; enabled: (root.canEdit || root.canAnnotate) && pdf.document.canUndo; onClicked: pdf.undo() }
                ActionButton { Layout.fillWidth: true; leftAligned: true; glyph: "redo"; text: "다시 실행"; hint: "Ctrl+Shift+Z"; enabled: (root.canEdit || root.canAnnotate) && pdf.document.canRedo; onClicked: pdf.redo() }
                Item { Layout.fillHeight: true }
                Text { Layout.fillWidth: true; text: "저장하면 변경 사항이 PDF에 반영됩니다."; wrapMode: Text.WordWrap; font.pixelSize: 12; color: "#919d86" }
            }
        }
    }

    footer: Rectangle {
        objectName: "readerFooter"; visible: !root.presenting
        height: 34; color: "#f8faf5"
        Rectangle { width: parent.width; height: 1; color: "#e0e6d9" }
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 15; anchors.rightMargin: 15; spacing: 9
            BusyIndicator { running: pdf.busy || pdf.ocrBusy; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            Text { text: pdf.ocrBusy ? pdf.ocrProgress : pdf.status; elide: Text.ElideRight; Layout.fillWidth: true; color: "#6d7583"; font.pixelSize: 12 }
            ActionButton { text: "정보"; implicitHeight: 28; onClicked: aboutDialog.open() }
            ActionButton { visible: pdf.ocrBusy; text: "OCR 취소"; implicitHeight: 28; onClicked: pdf.cancelOcr() }
            RowLayout {
                visible: root.hasDocument; spacing: 5
                ActionButton { glyph: "left"; hint: "이전 페이지 · ← / ↑ / Page Up"; implicitHeight: 28; enabled: pdf.currentPage>0; onClicked: root.turnPage(-1) }
                TextField { id: pageInput; objectName: "pageNumberInput"; text: pdf.currentPage+1; Layout.preferredWidth: 50; Layout.preferredHeight: 26; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 12; selectByMouse: true; validator: IntValidator { bottom: 1; top: Math.max(1,pdf.document.count) } onAccepted: { root.goPage(parseInt(text)-1); pages.forceActiveFocus(); } }
                Text { text: "/ " + pdf.document.count; color: "#6d7583"; font.pixelSize: 12 }
                ActionButton { glyph: "right"; hint: "다음 페이지 · → / ↓ / Page Down / Space"; implicitHeight: 28; enabled: pdf.currentPage<pdf.document.count-1; onClicked: root.turnPage(1) }
            }
        }
    }

    component DocumentPage: Item {
                    id: pageCell
                    required property int index
                    width: pageWidth
                    height: paper.height + 21
                    property real pageWidth: Math.max(80, ((pages.width-64-16*(root.pageColumns-1))/root.pageColumns)*root.zoom)
                    property real ratio: pdf.pageRatio(index)
                    property real pdfWidth: pdf.pageWidth(index)
                    property var pageBlocks: { pdf.blocks; return pdf.blocksAt(index); }
                    property bool near: !root.presenting && parent.parent.y+height >= pages.contentY-pages.height && parent.parent.y <= pages.contentY+pages.height*2
                    property string imageUrl: ""
                    property string renderError: ""
                    function request() {
                        imageUrl=pdf.imageUrl(index,"main");renderError=pdf.imageError(index,"main");ratio=pdf.pageRatio(index);pdfWidth=pdf.pageWidth(index);
                        if (near) { pdf.requestPage(index,"main",Math.ceil(pageWidth*Screen.devicePixelRatio)); pdf.requestText(index); if(root.tool==="editText") pdf.loadBlocksForPage(index); }
                        else pdf.releasePage(index,"main");
                    }
                    onNearChanged: request()
                    Connections { target: root; function onToolChanged(){if(root.tool==="editText" && pageCell.near) pdf.loadBlocksForPage(pageCell.index);} }
                    onPageWidthChanged: renderDelay.restart()
                    Component.onCompleted: request()
                    Timer { id: renderDelay; interval: 100; onTriggered: pageCell.request() }
                    Connections {
                        target: root.pdf
                        function onStateChanged() { pageCell.request(); }
                        function onPageImageChanged(page,kind) { if(page===pageCell.index && kind==="main") { pageCell.imageUrl=pdf.imageUrl(page,kind);pageCell.renderError=pdf.imageError(page,kind); } }
                        function onPageMetricsChanged(page) { if(page===pageCell.index) { pageCell.ratio=pdf.pageRatio(page);pageCell.pdfWidth=pdf.pageWidth(page); } }
                    }
                    Timer { interval: 700; repeat: true; running: pageCell.near && !pageCell.imageUrl && !pageCell.renderError; onTriggered: pageCell.request() }
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 3; width: paper.width+4; height: paper.height+2; color: "#dde1d8"; radius: 1 }
                    Rectangle {
                        id: paper; objectName: "paper" + pageCell.index
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: pageCell.pageWidth; height: width * pageCell.ratio
                        color: "white"; border.width: 1; border.color: "#d5dccf"
                        Image { anchors.fill: parent; anchors.margins: 1; source: pageCell.imageUrl; fillMode: Image.Stretch; cache: false; asynchronous: true; retainWhileLoading: true; smooth: true }
                        Text { visible: pageCell.imageUrl === ""; anchors.centerIn: parent; text: pageCell.renderError ? "페이지를 표시하지 못했어요." : "페이지 불러오는 중…"; color: "#9098a5"; font.pixelSize: 14 }
                        ActionButton { anchors.centerIn: parent; anchors.verticalCenterOffset: 40; visible: !pageCell.imageUrl && !!pageCell.renderError; text: "다시 불러오기"; outlined: true; z: 20; hint: pageCell.renderError; onClicked: pdf.retryPage(pageCell.index,"main",Math.ceil(pageCell.pageWidth*Screen.devicePixelRatio)) }
                        Repeater {
                            model: root.tool === "editText" && !textDialog.visible ? pageCell.pageBlocks : []
                            delegate: Rectangle {
                                required property var modelData
                                objectName: "textBlock"+pageCell.index+"_"+modelData.id
                                property real scale: paper.width/pageCell.pdfWidth
                                x: modelData.displayRect[0]*scale; y: modelData.displayRect[1]*scale
                                width: (modelData.displayRect[2]-modelData.displayRect[0])*scale
                                height: (modelData.displayRect[3]-modelData.displayRect[1])*scale
                                color: blockMouse.containsMouse ? "#194b7851" : "transparent"
                                border.color: "#8da689"; border.width: 1; radius: 2
                                MouseArea { id: blockMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.IBeamCursor; enabled: root.canEdit; onClicked: pdf.editBlock(parent.modelData) }
                            }
                        }
                        Repeater {
                            model: pdf.searchResults
                            delegate: Item {
                                required property var modelData
                                anchors.fill: parent
                                Repeater {
                                    model: modelData.page === pageCell.index ? modelData.rects : []
                                    delegate: Rectangle {
                                        required property var modelData
                                        property real scale: paper.width/pageCell.pdfWidth
                                        x: modelData[0]*scale; y: modelData[1]*scale
                                        width: (modelData[2]-modelData[0])*scale; height: (modelData[3]-modelData[1])*scale
                                        color: "#66ffcf32"; border.color: "#dba914"; radius: 1
                                    }
                                }
                            }
                        }
                        Rectangle {
                            property var hit: pdf.activeSearchHit
                            property real factor: paper.width/pageCell.pdfWidth
                            visible: hit.page===pageCell.index && !!hit.rect
                            x: hit.rect ? hit.rect[0]*factor-2 : 0; y: hit.rect ? hit.rect[1]*factor-2 : 0
                            width: hit.rect ? (hit.rect[2]-hit.rect[0])*factor+4 : 0
                            height: hit.rect ? (hit.rect[3]-hit.rect[1])*factor+4 : 0
                            color: "#66ed9a42"; border.color: "#bd7330"; border.width: 2; radius: 2
                        }
                        Rectangle {
                            property var annotation: pdf.selectedAnnotation
                            property real factor: paper.width/pageCell.pdfWidth
                            visible: root.workspaceMode==="comments" && annotation.page===pageCell.index && !!annotation.rect
                            x: annotation.rect ? annotation.rect[0]*factor-3 : 0; y: annotation.rect ? annotation.rect[1]*factor-3 : 0
                            width: annotation.rect ? (annotation.rect[2]-annotation.rect[0])*factor+6 : 0
                            height: annotation.rect ? (annotation.rect[3]-annotation.rect[1])*factor+6 : 0
                            color: "transparent"; border.color: "#6c8d62"; border.width: 1; radius: 2
                        }
                        TextLayer {
                            controller: root.pdf
                            allowEdits: !textDialog.visible && !annotationEditor.visible
                            onMenuOpenChanged: root.readerMenuOpen=menuOpen
                            anchors.fill: parent; pageNumber: pageCell.index; pdfWidth: pageCell.pdfWidth; viewport: pages
                            markupTool: ["highlight","underline","strikeout"].indexOf(root.tool)>=0 ? root.tool : ""
                            visible: root.tool === "read" || !!markupTool; enabled: visible && !pdf.busy
                        }
                        InlineTextEditor { session: textDialog; controller: root.pdf; pageNumber: pageCell.index; factor: paper.width/pageCell.pdfWidth }
                        LegacyTextEditor { session: textDialog; controller: root.pdf; pageNumber: pageCell.index; factor: paper.width/pageCell.pdfWidth }
                        ImageHandles {
                            anchors.fill: parent; z: 50; controller: root.pdf
                            objects: { pdf.textTick; return pdf.textLayout(pageCell.index).movableImages || []; }
                            factor: paper.width/pageCell.pdfWidth; pdfWidth: pageCell.pdfWidth; pdfHeight: pageCell.pdfWidth*pageCell.ratio
                            editing: root.tool==="imageMove" && root.canEdit
                        }
                        HoverHandler { enabled: root.tool === "hand"; cursorShape: Qt.OpenHandCursor }
                        MouseArea {
                            id: region; anchors.fill: parent
                            enabled: (root.canEdit && ["addText", "image"].indexOf(root.tool)>=0) || (root.canAnnotate && root.tool==="note")
                            cursorShape: root.tool === "read" ? Qt.IBeamCursor : Qt.CrossCursor
                            property point start: Qt.point(0,0)
                            property point end: Qt.point(0,0)
                            onPressed: function(mouse) { start = Qt.point(mouse.x,mouse.y); end=start; }
                            onPositionChanged: function(mouse) { if (pressed) end = Qt.point(mouse.x,mouse.y); }
                            onReleased: function(mouse) {
                                end = Qt.point(mouse.x,mouse.y);
                                var s = pageCell.pdfWidth/paper.width;
                                var r = [Math.min(start.x,end.x)*s, Math.min(start.y,end.y)*s, Math.max(start.x,end.x)*s, Math.max(start.y,end.y)*s];
                                if (root.tool==="note" || (r[2]-r[0] > 3 && r[3]-r[1] > 3)) pdf.regionAction(pageCell.index, r, root.tool);
                            }
                        }
                        Rectangle {
                            visible: region.pressed; x: Math.min(region.start.x,region.end.x); y: Math.min(region.start.y,region.end.y)
                            width: Math.abs(region.start.x-region.end.x); height: Math.abs(region.start.y-region.end.y)
                            border.color: "#51765a"; color: "#224b7851"; border.width: 1
                        }
                    }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; y: paper.height+5; text: pageCell.index+1; font.pixelSize: 12; color: "#777e8a" }
                }

    Loader {
        id: presentation; anchors.fill: parent; z: 100
        active: root.presenting; visible: active
        sourceComponent: PresentationView {
            controller: root.pdf
            onPageRequested: function(page) { root.goPage(page); }
            onExitRequested: root.endPresentation()
        }
        onLoaded: item.forceActiveFocus()
    }

    Connections {
        target: root.tabWorkspace
        function onAboutToSwitch() { root.saveView(); }
        function onActiveChanged() { root.restoreView(); }
        function onCloseApproved() { root.quitApplication(); }
        function onShowError(message) { errorDialog.message=message; errorDialog.open(); }
    }
    Timer {
        id: navigationTimer; interval: 35; repeat: true
        onTriggered: {
            var nav=root.pendingNavigation;
            if(!nav || nav.owner!==root.pdf) { stop(); root.restoring=false; return; }
            pages.forceLayout();
            var cell=root.cellForPage(nav.page);
            if(!cell) pages.positionViewAtIndex(root.rowForPage(nav.page),ListView.Beginning);
            else {
                var minY=pages.originY-pages.topMargin;
                var maxY=Math.max(minY,pages.originY+pages.contentHeight-pages.height+pages.bottomMargin);
                var y=nav.offset!==undefined ? root.cellTop(cell)+nav.offset*cell.pageWidth : root.cellTop(cell)+nav.y*cell.pageWidth/cell.pdfWidth-pages.height*.25;
                pages.contentY=Math.max(minY,Math.min(maxY,y));
                if(nav.horizontal!==undefined) pages.contentX=nav.horizontal*pages.contentWidth;
                else {
                    var x=cell.mapToItem(pages.contentItem,0,0).x+nav.x*cell.pageWidth/cell.pdfWidth;
                    if(x<pages.contentX+24 || x>pages.contentX+pages.width-80) pages.contentX=Math.max(0,Math.min(pages.contentWidth-pages.width,x-pages.width*.25));
                }
                pdf.setCurrentPage(nav.page);
            }
            nav.tries++;
            if(nav.tries>=12 || (cell && cell.imageUrl && nav.tries>=3)) { stop(); root.pendingNavigation=null; root.restoring=false; }
        }
    }
    Timer { id: searchDelay; interval: 300; onTriggered: pdf.search(root.pendingQuery) }
    Timer {
        interval: 35; repeat: true; running: root.draggedPage >= 0
        onTriggered: {
            var step = root.dragViewportY < 40 ? -12 : root.dragViewportY > thumbs.height-40 ? 12 : 0;
            if (step === 0) return;
            thumbs.contentY = Math.max(0, Math.min(thumbs.contentHeight-thumbs.height, thumbs.contentY+step));
            var index = thumbs.indexAt(thumbs.width/2, thumbs.contentY+root.dragViewportY);
            if (index >= 0) { var cell=thumbs.itemAtIndex(index); root.dropIndex=index+(cell && thumbs.contentY+root.dragViewportY>cell.y+cell.height/2 ? 1 : 0); }
        }
    }
    Connections {
        target: root.pdf
        function onOpenMergeDialog() { mergeDialog.open(); }
        function onOpenComments() { root.workspaceMode="comments"; }
        function onShowAnnotationEditor(data) { annotationEditor.compose(data); }
        function onNavigateRequested(page,x,y) { root.jumpTo(page,x,y); }
        function onTextCommitted() { textDialog.close(); root.finishDraftClose(); }
        function onAnnotationCommitted() { annotationEditor.close(); if(root.tool==="note") root.tool="read"; root.finishDraftClose(); }
        function onImageInserted() { root.useTool("imageMove"); }
        function onShowTextEditor(data) { textDialog.compose(data); }
        function onShowError(message) { root.closeAfterEdit=false; if(!root.tabWorkspace) { errorDialog.message = message; errorDialog.open(); } }
        function onStateChanged() {
            if (!root.presenting && root.tool === "editText" && root.hasDocument && !pdf.busy) pdf.loadBlocks(pdf.currentPage);
        }
        function onSelectionChanged() {
            if(root.sidebarOpen) thumbs.positionViewAtIndex(pdf.currentPage,ListView.Contain);
            if (!root.presenting && root.tool === "editText" && root.hasDocument) pdf.loadBlocks(pdf.currentPage);
        }
    }

    MergeDialog { id: mergeDialog; controller: root.pdf }

    Connections { target: pdf.liveEditor; function onApplyFailed(){root.closeAfterEdit=false;} }
    property bool closeAfterEdit: false
    function finishDraftClose() {
        if(!closeAfterEdit)return;
        closeAfterEdit=false; Qt.callLater(function(){root.close();});
    }
    Dialog {
        id: draftClose; objectName: "draftCloseDialog"; anchors.centerIn: parent
        title: "편집 중인 내용"; width: 510; modal: true; closePolicy: Popup.NoAutoClose
        contentItem: ColumnLayout {
            spacing: 18
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "아직 적용하지 않은 편집 내용이 있어요. 어떻게 닫을까요?" }
            Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#7a6b4b"; visible: textDialog.visible && !pdf.liveEditor.canApply && textDialog.targetData.mode==="replace"; text: "글꼴 확인이나 오류 해결 전에는 적용할 수 없어요. 편집으로 돌아가거나 이번 입력을 버리고 닫을 수 있어요." }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                ActionButton { objectName: "continueEditing"; text: "계속 편집"; onClicked: {root.closeAfterEdit=false;root.closeAllRequested=false;draftClose.close();} }
                ActionButton { objectName: "discardDraftClose"; text: "입력 버리고 닫기"; enabled: !pdf.busy; onClicked: {root.closeAfterEdit=false;draftClose.close();textDialog.close();annotationEditor.close();Qt.callLater(function(){root.close();});} }
                ActionButton { objectName: "applyDraftClose"; text: "적용 후 닫기"; primary: true; enabled: !pdf.busy && (textDialog.visible ? (textDialog.targetData.mode!=="replace" || pdf.liveEditor.canApply) : annotationEditor.canApply); onClicked: {root.closeAfterEdit=true;draftClose.close();if(textDialog.visible)pdf.applyText(textDialog.targetData,textDialog.text,textDialog.fontSize,textDialog.areaHeight);else annotationEditor.apply();} }
            }
        }
    }

    QtObject {
        id: textDialog; objectName: "textEditorSession"
        property bool visible: false
        property var targetData: ({})
        property string text: ""
        property real fontSize: 14
        property real areaHeight: 40
        property string fallbackFont: root.uiFontFamily
        onVisibleChanged: pdf.setTextEditorVisible(visible)
        function close() { visible=false; }
        function compose(data) {
            if(visible) return;
            targetData=data; text=data.text || ""; fontSize=Number(data.size || 14);
            areaHeight=data.mode==="replace" ? data.rect[3]-data.rect[1]+10 : data.height;
            visible=true;
        }
    }

    Dialog {
        id: ocrDialog; anchors.centerIn: parent; width: 510; modal: true; title: "문자 인식 · OCR"
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 15
            Text { Layout.fillWidth: true; text: "스캔 페이지에 검색 가능한 문자층을 추가해요. 이미 텍스트가 있는 페이지는 건너뛰며, 원본 이미지는 유지합니다."; wrapMode: Text.WordWrap; color: "#657081" }
            Text { Layout.fillWidth: true; visible: pdf.languages.length === 0; text: "OCR 언어 데이터를 찾지 못했어요. 설치 프로그램으로 다시 설치해 주세요."; wrapMode: Text.WordWrap; color: "#ac5d25" }
            Text { text: "인식 범위"; font.weight: Font.DemiBold; color: "#394252" }
            ComboBox { id: ocrScope; Layout.fillWidth: true; model: ["현재 페이지", "선택한 페이지", "전체 문서"] }
            Text { text: "인식 언어"; font.weight: Font.DemiBold; color: "#394252" }
            ComboBox {
                id: ocrLanguage; Layout.fillWidth: true
                model: pdf.languages.indexOf("kor")>=0 && pdf.languages.indexOf("eng")>=0 ? ["kor+eng"].concat(pdf.languages.filter(function(x){return x!=="osd";})) : pdf.languages.filter(function(x){return x!=="osd";})
            }
            Text { visible: pdf.languages.length > 0 && pdf.languages.indexOf("kor") < 0; text: "한국어 데이터(kor)가 아직 설치되어 있지 않아요."; color: "#ac5d25"; font.pixelSize: 13 }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                ActionButton { text: "취소"; onClicked: ocrDialog.close() }
                ActionButton { text: "OCR 시작"; primary: true; enabled: ocrLanguage.count>0; onClicked: { pdf.startOcr(["current","selected","all"][ocrScope.currentIndex],ocrLanguage.currentText); ocrDialog.close(); } }
            }
        }
    }

    Dialog {
        id: settingsDialog; objectName: "settingsDialog"; parent: Overlay.overlay; anchors.centerIn: parent; width: 490; modal: true; title: "설정"
        standardButtons: Dialog.Ok
        contentItem: ScrollView {
            id: settingsScroll; objectName: "settingsScroll"; clip: true
            implicitHeight: Math.min(settingsContent.implicitHeight, Math.max(200, root.height - 170))
            contentWidth: availableWidth
            contentHeight: settingsContent.implicitHeight
            ColumnLayout {
                id: settingsContent; width: settingsScroll.availableWidth
                spacing: 14
                ColumnLayout {
                    objectName: "defaultAppsSection"; Layout.fillWidth: true; visible: Qt.platform.os === "windows"; spacing: 6
                    ActionButton { objectName: "defaultAppsButton"; text: "기본 PDF 앱 설정"; onClicked: { settingsDialog.close(); pdf.openDefaultAppsSettings(); } }
                    Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Windows 설정에서 .pdf의 앱을 윤DF로 선택하면 PDF를 더블클릭해 열 수 있어요."; color: "#6d7888"; font.pixelSize: 13 }
                }
                Text { text: "마우스 휠 속도  ·  " + pdf.wheelSpeed.toFixed(1) + "배"; color: "#394252" }
                Slider { Layout.fillWidth: true; from: .5; to: 5; stepSize: .1; value: pdf.wheelSpeed; onMoved: pdf.setWheelSpeed(value) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Windows의 휠 줄 수 설정에 배율을 적용합니다. 무한 휠의 입력량을 모두 반영하며 터치패드의 픽셀 이동은 그대로 유지합니다."; color: "#6d7888"; font.pixelSize: 13 }
                ActionButton { text: "기본 속도 (1배)"; onClicked: pdf.setWheelSpeed(1) }
                Text { text: "페이지 이미지 캐시"; color: "#394c3c"; Layout.topMargin: 8 }
                ComboBox { Layout.fillWidth: true; model: ["256 MB · 절약","512 MB · 권장","1 GB · 많은 페이지 재사용"]; currentIndex: pdf.cacheMiB>=1024 ? 2 : pdf.cacheMiB>=512 ? 1 : 0; onActivated: pdf.setCacheMiB([256,512,1024][currentIndex]) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "한번 본 페이지를 메모리에 보관해 다시 열 때 빠르게 표시합니다. 미리보기·PDF 엔진·그래픽 메모리는 별도로 사용합니다."; color: "#809078"; font.pixelSize: 12 }
                ComboBox { Layout.fillWidth: true; model: ["그래픽 가속 · 자동","호환 모드 · 화면 표시 문제가 있을 때"]; currentIndex: pdf.graphicsMode === "software" ? 1 : 0; onActivated: pdf.setGraphicsMode(currentIndex ? "software" : "auto") }
                Text { text: "그래픽 설정은 앱을 다시 실행하면 적용됩니다."; color: "#8c9984"; font.pixelSize: 12 }
                CheckBox { text: "현재 보는 스캔 페이지 자동 OCR"; checked: pdf.automaticOcr; onToggled: pdf.setAutomaticOcr(checked) }
                Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "일반 PDF의 글자는 바로 선택할 수 있습니다. 스캔은 인식이 끝나면 선택할 수 있으며, 저장하면 문자층이 PDF에 남습니다."; color: "#6d7888"; font.pixelSize: 13 }
                ActionButton { text: "오류 로그 폴더 열기"; onClicked: pdf.openLogFolder() }
            }
        }
    }

    Dialog {
        id: aboutDialog; anchors.centerIn: parent; width: 650; height: 570; modal: true; title: "윤DF · 0.9.2"
        standardButtons: Dialog.Ok
        contentItem: ColumnLayout {
            Text { text: "Copyright © 2026 YoonDF contributors"; color: "#384253" }
            Text { text: "AGPL-3.0-or-later · 이 라이선스에 따라 수정·재배포할 수 있습니다.\n보증 없이 제공됩니다. 전체 소스와 빌드 스크립트는 배포 압축파일에 포함됩니다."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#657081"; font.pixelSize: 13 }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                TextArea { readOnly: true; selectByMouse: true; text: aboutDialog.visible ? pdf.licenseText() : ""; wrapMode: TextEdit.Wrap; font.pixelSize: 12 }
            }
        }
    }

    Dialog {
        id: errorDialog; anchors.centerIn: parent; width: 520; modal: true; title: "확인해 주세요"
        property string message: ""
        standardButtons: Dialog.Ok
        contentItem: Text { text: errorDialog.message; wrapMode: Text.WordWrap; color: "#414a59"; font.pixelSize: 14 }
    }
}
