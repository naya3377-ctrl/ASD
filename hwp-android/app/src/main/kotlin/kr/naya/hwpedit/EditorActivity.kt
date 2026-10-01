package kr.naya.hwpedit

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.content.res.Configuration
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.Editable
import android.text.InputType
import android.text.Spanned
import android.text.TextWatcher
import android.text.style.AbsoluteSizeSpan
import android.text.style.LeadingMarginSpan
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import kr.naya.hwpedit.core.BoxBlock
import kr.naya.hwpedit.core.DocModel
import kr.naya.hwpedit.core.DocumentException
import kr.naya.hwpedit.core.HwpDocuments
import kr.naya.hwpedit.core.ImageBlock
import kr.naya.hwpedit.core.ObjectBlock
import kr.naya.hwpedit.core.TableBlock
import kr.naya.hwpedit.ui.DocText
import kr.naya.hwpedit.ui.DocumentRenderer
import kr.naya.hwpedit.ui.EdgeToEdge
import kr.naya.hwpedit.ui.FindSpan
import kr.naya.hwpedit.ui.FlowEditText
import kr.naya.hwpedit.ui.Palette
import kr.naya.hwpedit.ui.TopBar
import kr.naya.hwpedit.ui.UndoManager
import kr.naya.hwpedit.ui.divider
import kr.naya.hwpedit.ui.dp
import kr.naya.hwpedit.ui.iconButton
import kr.naya.hwpedit.ui.label
import kr.naya.hwpedit.ui.pillButton
import kr.naya.hwpedit.ui.ripple
import kr.naya.hwpedit.ui.roundRect
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.roundToInt

/** 문서 화면: 읽기, 고치기, 저장. */
class EditorActivity : Activity() {

    private val io: ExecutorService = Executors.newSingleThreadExecutor()
    private val imageIo: ExecutorService = Executors.newFixedThreadPool(2)
    private val main = Handler(Looper.getMainLooper())

    private lateinit var root: LinearLayout
    private lateinit var topBar: TopBar
    private lateinit var banner: TextView
    private lateinit var findBar: LinearLayout
    private lateinit var findInput: EditText
    private lateinit var findCount: TextView
    private lateinit var body: FrameLayout
    private lateinit var scroll: ScrollView
    private lateinit var page: LinearLayout
    private lateinit var overlay: LinearLayout
    private lateinit var overlayText: TextView

    private lateinit var btnSearch: ImageButton
    private lateinit var btnEdit: TextView
    private lateinit var btnUndo: ImageButton
    private lateinit var btnRedo: ImageButton
    private lateinit var btnSave: TextView
    private lateinit var btnDone: TextView
    private lateinit var btnMore: ImageButton

    private var uri: Uri? = null
    private var displayName = "문서"
    private var isNewDocument = false
    private var original: ByteArray? = null
    private var model: DocModel? = null

    private val flows = ArrayList<FlowEditText>()
    private var editMode = false
    private var dirtyHint = false
    private var busy = false
    private var buildToken = 0
    private var building = false
    private var renderedWidth = 0
    private var saveAsThenFinish = false
    private var editHintShown = false

    private val undo = UndoManager { updateActions() }

    private class Match(val flow: FlowEditText, val start: Int)

    private var matches: List<Match> = emptyList()
    private var currentMatch = -1
    private val findRunnable = Runnable { runFind() }

    // ---------------------------------------------------------------- 화면 만들기

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        EdgeToEdge.enable(this)
        buildChrome()

        isNewDocument = intent.getBooleanExtra(EXTRA_NEW, false)
        if (isNewDocument) {
            displayName = "새 문서.hwp"
        } else {
            uri = sourceUri(intent)
            if (uri == null) {
                showError("열 문서를 찾지 못했어요.")
                return
            }
            if (Recents.keepPermission(this, uri!!, intent.flags)) {
                Recents(this).add(uri!!, Files.displayName(contentResolver, uri!!))
            }
        }
        load()
    }

    private fun sourceUri(intent: Intent): Uri? {
        intent.data?.let { return it }
        if (intent.action == Intent.ACTION_SEND) {
            return if (Build.VERSION.SDK_INT >= 33) {
                intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri
            }
        }
        return null
    }

    private fun buildChrome() {
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Palette.SURFACE)
        }

        topBar = TopBar(this)
        topBar.setLeading(iconButton(R.drawable.ic_back, "뒤로") { handleBack() })
        btnSearch = iconButton(R.drawable.ic_search, "찾기") { openFind() }
        btnUndo = iconButton(R.drawable.ic_undo, "되돌리기") { undo.undo() }
        btnRedo = iconButton(R.drawable.ic_redo, "다시 하기") { undo.redo() }
        btnEdit = textButton("편집") { setEditMode(true) }
        btnSave = textButton("저장") { save(saveAs = false, thenFinish = false) }
        btnDone = textButton("완료") { setEditMode(false) }
        btnMore = iconButton(R.drawable.ic_more, "더 보기") { showMenu(it) }
        topBar.setActions(btnSearch, btnUndo, btnRedo, btnEdit, btnSave, btnDone, btnMore)
        root.addView(topBar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        banner = label("", 14f, 0xFF7A5B00.toInt()).apply {
            setBackgroundColor(0xFFFFF4D6.toInt())
            setPadding(dp(16), dp(10), dp(16), dp(10))
            visibility = View.GONE
        }
        root.addView(banner)

        findBar = buildFindBar()
        root.addView(findBar)
        root.addView(divider())

        body = FrameLayout(this)
        scroll = ScrollView(this).apply {
            setBackgroundColor(Palette.BACKGROUND)
            isFillViewport = true
            clipToPadding = false
        }
        val pageHolder = FrameLayout(this).apply { setPadding(dp(PAGE_MARGIN_DP), dp(10), dp(PAGE_MARGIN_DP), dp(24)) }
        page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = roundRect(Palette.SURFACE, dp(6).toFloat(), Palette.LINE, max(1, dp(0.5f)))
            setPadding(dp(PAGE_PADDING_DP), dp(20), dp(PAGE_PADDING_DP), dp(28))
        }
        pageHolder.addView(page, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        scroll.addView(pageHolder)
        body.addView(scroll, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))

        overlay = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(0x99FFFFFF.toInt())
            isClickable = true
            isFocusable = true
            visibility = View.GONE
        }
        overlay.addView(ProgressBar(this).apply {
            indeterminateTintList = ColorStateList.valueOf(Palette.ACCENT)
        })
        overlayText = label("", 15f, Palette.TEXT).apply {
            setPadding(0, dp(12), 0, 0)
            gravity = Gravity.CENTER
        }
        overlay.addView(overlayText)
        body.addView(overlay, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))

        root.addView(body, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
        EdgeToEdge.apply(root, topBar, body)
        updateActions()
    }

    private fun textButton(text: String, onClick: (View) -> Unit): TextView =
        label(text, 16f, Palette.ACCENT, bold = true).apply {
            gravity = Gravity.CENTER
            minWidth = dp(56)
            minHeight = dp(44)
            setPadding(dp(12), 0, dp(12), 0)
            background = ripple(null, dp(22).toFloat())
            isClickable = true
            isFocusable = true
            setOnClickListener(onClick)
        }

    private fun buildFindBar(): LinearLayout {
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(Palette.SURFACE)
            setPadding(dp(12), dp(4), dp(4), dp(6))
            visibility = View.GONE
        }
        findInput = EditText(this).apply {
            hint = "찾을 말"
            isSingleLine = true
            inputType = InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_SEARCH
            background = roundRect(Palette.BACKGROUND, dp(18).toFloat())
            setPadding(dp(14), dp(8), dp(14), dp(8))
            setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 15f)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    main.removeCallbacks(findRunnable)
                    main.postDelayed(findRunnable, 250)
                }
            })
            setOnEditorActionListener { _, actionId, event ->
                if (actionId == EditorInfo.IME_ACTION_SEARCH ||
                    (event?.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)
                ) {
                    moveMatch(+1)
                    true
                } else {
                    false
                }
            }
        }
        bar.addView(findInput, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        findCount = label("", 13f, Palette.SUBTEXT).apply { setPadding(dp(10), 0, dp(4), 0) }
        bar.addView(findCount)
        bar.addView(iconButton(R.drawable.ic_up, "이전") { moveMatch(-1) })
        bar.addView(iconButton(R.drawable.ic_down, "다음") { moveMatch(+1) })
        bar.addView(iconButton(R.drawable.ic_close, "찾기 닫기") { closeFind() })
        return bar
    }

    private fun updateActions() {
        val m = model
        val canEdit = m != null && m.readOnlyReason == null && !busy
        btnSearch.visibility = if (!editMode && m != null) View.VISIBLE else View.GONE
        btnEdit.visibility = if (!editMode && canEdit) View.VISIBLE else View.GONE
        btnUndo.visibility = if (editMode) View.VISIBLE else View.GONE
        btnRedo.visibility = if (editMode) View.VISIBLE else View.GONE
        btnSave.visibility = if (editMode || dirtyHint) View.VISIBLE else View.GONE
        btnDone.visibility = if (editMode) View.VISIBLE else View.GONE
        btnMore.visibility = if (m != null) View.VISIBLE else View.GONE
        btnUndo.isEnabled = undo.canUndo
        btnUndo.alpha = if (undo.canUndo) 1f else 0.35f
        btnRedo.isEnabled = undo.canRedo
        btnRedo.alpha = if (undo.canRedo) 1f else 0.35f
        btnSave.setTextColor(if (dirtyHint) Palette.ACCENT else Palette.SUBTEXT)
        topBar.title.text = if (dirtyHint) "• $displayName" else displayName
    }

    // ---------------------------------------------------------------- 열기

    private fun load() {
        showOverlay("문서를 여는 중…")
        val source = uri
        io.execute {
            try {
                val bytes = if (isNewDocument) {
                    assets.open("blank.hwp").use { it.readBytes() }
                } else {
                    Files.read(contentResolver, source!!)
                }
                val name = if (isNewDocument) displayName else Files.displayName(contentResolver, source!!)
                val opened = HwpDocuments.open(bytes)
                main.post { onLoaded(bytes, opened.model, name) }
            } catch (e: DocumentException) {
                main.post { showError(e.message ?: "문서를 열지 못했어요.") }
            } catch (e: SecurityException) {
                main.post { showError("이 파일을 읽을 권한이 없어요. 파일 관리자에서 다시 열어 주세요.") }
            } catch (e: OutOfMemoryError) {
                main.post { showError("문서가 너무 커서 열 수 없어요.") }
            } catch (e: Exception) {
                main.post { showError("파일을 읽지 못했어요.\n(${e.message ?: e.javaClass.simpleName})") }
            }
        }
    }

    private fun onLoaded(bytes: ByteArray, m: DocModel, name: String) {
        if (isFinishing || isDestroyed) return
        original = bytes
        model = m
        displayName = name
        hideOverlay()
        val ro = m.readOnlyReason
        if (ro != null) {
            banner.text = ro
            banner.visibility = View.VISIBLE
        }
        render(m, preserved = null, scrollY = 0)
        if (isNewDocument) setEditMode(true)
        updateActions()
    }

    private fun showError(message: String) {
        hideOverlay()
        page.removeAllViews()
        page.addView(label("문서를 열 수 없어요", 20f, Palette.TEXT, bold = true))
        page.addView(label(message, 15f, Palette.SUBTEXT).apply { setPadding(0, dp(10), 0, dp(24)) })
        page.addView(pillButton("닫기", primary = true) { finish() },
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        model = null
        updateActions()
    }

    // ---------------------------------------------------------------- 그리기

    private fun contentWidth(): Int {
        val total = if (root.width > 0) root.width - root.paddingLeft - root.paddingRight else resources.displayMetrics.widthPixels
        return max(dp(160), total - dp(PAGE_MARGIN_DP) * 2 - dp(PAGE_PADDING_DP) * 2)
    }

    /**
     * 문서를 화면에 그린다. 큰 문서도 바로 보이도록 조금씩 나눠서 만든다.
     * @param preserved 다시 그리기 전 입력칸 내용(flowId -> 글). 고친 내용을 잃지 않기 위해 쓴다.
     */
    private fun render(m: DocModel, preserved: Map<Int, CharSequence>?, scrollY: Int) {
        val token = ++buildToken
        flows.clear()
        page.removeAllViews()
        undo.clear()
        renderedWidth = contentWidth()
        val renderer = DocumentRenderer(this, m, Prefs.textScale(this), renderedWidth, imageIo, main) { v ->
            preserved?.get(v.flowId)?.let { v.setText(it) }
            registerFlow(v)
        }
        val builders = renderer.topLevelBuilders()
        building = true
        var index = 0
        var first = true
        fun step() {
            if (token != buildToken || isDestroyed) return
            val budget = if (first) 120L else 14L
            first = false
            val t0 = SystemClock.uptimeMillis()
            while (index < builders.size && SystemClock.uptimeMillis() - t0 < budget) {
                val v = builders[index++]()
                page.addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            }
            if (index < builders.size) {
                main.post { step() }
            } else {
                building = false
                if (flows.isEmpty() && builders.isEmpty()) {
                    page.addView(label("빈 문서예요.", 15f, Palette.SUBTEXT))
                }
                if (scrollY > 0) scroll.post { scroll.scrollTo(0, scrollY) }
            }
        }
        step()
    }

    private fun registerFlow(v: FlowEditText) {
        v.editable = editMode
        undo.watch(v)
        v.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (!dirtyHint) {
                    dirtyHint = true
                    updateActions()
                }
            }
        })
        flows.add(v)
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        val m = model ?: return
        root.post {
            val w = contentWidth()
            if (abs(w - renderedWidth) > dp(8)) {
                val ratio = scroll.scrollY.toFloat() / max(1, scroll.getChildAt(0).height)
                val preserved = flows.associate { it.flowId to (it.text as CharSequence) }
                render(m, preserved, 0)
                scroll.postDelayed({ scroll.scrollTo(0, (ratio * scroll.getChildAt(0).height).roundToInt()) }, 300)
            }
        }
    }

    // ---------------------------------------------------------------- 보기 / 편집

    private fun setEditMode(on: Boolean) {
        val m = model ?: return
        val ro = m.readOnlyReason
        if (on && ro != null) {
            toast(ro)
            return
        }
        editMode = on
        for (f in flows) f.editable = on
        if (!on) {
            hideKeyboard()
            currentFocus?.clearFocus()
        } else {
            closeFind()
            if (!editHintShown) {
                editHintShown = true
                toast("고칠 곳을 누르면 글을 고칠 수 있어요. 다 고치면 '저장'을 누르세요.")
            }
        }
        updateActions()
    }

    private fun hideKeyboard() {
        val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager ?: return
        imm.hideSoftInputFromWindow(root.windowToken, 0)
    }

    // ---------------------------------------------------------------- 저장

    private fun collectEdits(): Map<Int, String> {
        val edits = HashMap<Int, String>()
        for (f in flows) {
            val t = f.modelText()
            if (t != f.originalText) edits[f.flowId] = t
        }
        return edits
    }

    private fun save(saveAs: Boolean, thenFinish: Boolean) {
        val m = model ?: return
        val orig = original ?: return
        if (busy) return
        val ro = m.readOnlyReason
        if (ro != null && !saveAs) {
            toast(ro)
            return
        }
        val target = uri
        if (saveAs || target == null) {
            launchSaveAs(thenFinish)
            return
        }
        val edits = collectEdits()
        if (edits.isEmpty()) {
            dirtyHint = false
            updateActions()
            if (thenFinish) finish() else toast("바뀐 내용이 없어요.")
            return
        }
        doSave(target, orig, edits, m, thenFinish)
    }

    private fun launchSaveAs(thenFinish: Boolean) {
        val m = model ?: return
        saveAsThenFinish = thenFinish
        val base = displayName.substringBeforeLast('.', displayName)
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = m.format.mimeType
            putExtra(Intent.EXTRA_TITLE, "$base.${m.format.extension}")
        }
        try {
            startActivityForResult(intent, REQ_SAVE_AS)
        } catch (e: Exception) {
            toast("저장 위치를 고르는 화면을 열 수 없어요.")
        }
    }

    @Deprecated("Activity 기본 결과 처리")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_SAVE_AS || resultCode != RESULT_OK) return
        val target = data?.data ?: return
        val m = model ?: return
        val orig = original ?: return
        val kept = Recents.keepPermission(this, target, data.flags)
        val name = Files.displayName(contentResolver, target)
        displayNameAfterSave = name
        doSave(target, orig, collectEdits(), m, saveAsThenFinish) { if (kept) Recents(this).add(target, name) }
    }

    private var displayNameAfterSave: String? = null

    private fun doSave(
        target: Uri,
        orig: ByteArray,
        edits: Map<Int, String>,
        m: DocModel,
        thenFinish: Boolean,
        afterSuccess: (() -> Unit)? = null,
    ) {
        busy = true
        for (f in flows) f.editable = false
        showOverlay("저장하는 중…")
        updateActions()
        io.execute {
            try {
                val bytes = if (edits.isEmpty()) orig else HwpDocuments.save(orig, edits, m)
                Files.write(contentResolver, target, bytes)
                val reopened = HwpDocuments.open(bytes).model
                main.post {
                    afterSuccess?.invoke()
                    onSaved(target, bytes, reopened, thenFinish)
                }
            } catch (e: SecurityException) {
                main.post { onSaveFailed("이 위치에는 저장할 권한이 없어요.", offerSaveAs = true) }
            } catch (e: DocumentException) {
                main.post { onSaveFailed(e.message ?: "저장하지 못했어요.", offerSaveAs = false) }
            } catch (e: OutOfMemoryError) {
                main.post { onSaveFailed("메모리가 부족해서 저장하지 못했어요.", offerSaveAs = false) }
            } catch (e: Exception) {
                main.post { onSaveFailed("저장하지 못했어요.\n(${e.message ?: e.javaClass.simpleName})", offerSaveAs = true) }
            }
        }
    }

    private fun onSaveFailed(message: String, offerSaveAs: Boolean) {
        busy = false
        hideOverlay()
        for (f in flows) f.editable = editMode
        updateActions()
        val b = AlertDialog.Builder(this).setTitle("저장하지 못했어요").setMessage(message)
        if (offerSaveAs) {
            b.setPositiveButton("다른 이름으로 저장") { _, _ -> launchSaveAs(false) }
            b.setNegativeButton("닫기", null)
        } else {
            b.setPositiveButton("확인", null)
        }
        b.show()
    }

    private fun onSaved(target: Uri, bytes: ByteArray, newModel: DocModel, thenFinish: Boolean) {
        busy = false
        hideOverlay()
        original = bytes
        uri = target
        isNewDocument = false
        displayNameAfterSave?.let { displayName = it }
        displayNameAfterSave = null
        if (thenFinish) {
            toast("저장했어요.")
            finish()
            return
        }
        // 화면 구성이 그대로면 입력칸을 새 문서에 다시 연결만 한다(커서·되돌리기 기록 유지).
        val newFlows = newModel.allFlows()
        val sameShape = !building && newFlows.size == flows.size &&
            newFlows.indices.all { newFlows[it].text == flows[it].modelText() }
        model = newModel
        if (sameShape) {
            for (i in newFlows.indices) {
                flows[i].flowId = newFlows[i].flowId
                flows[i].originalText = newFlows[i].text
            }
            for (f in flows) f.editable = editMode
        } else {
            render(newModel, preserved = null, scrollY = scroll.scrollY)
        }
        dirtyHint = false
        updateActions()
        toast("저장했어요.")
    }

    // ---------------------------------------------------------------- 나가기

    private fun handleBack() {
        if (findBar.visibility == View.VISIBLE) {
            closeFind()
            return
        }
        if (busy) return
        if (model != null && (collectEdits().isNotEmpty() || (isNewDocument && dirtyHint))) {
            AlertDialog.Builder(this)
                .setMessage("저장하지 않은 내용이 있어요. 저장할까요?")
                .setPositiveButton("저장") { _, _ -> save(saveAs = false, thenFinish = true) }
                .setNegativeButton("저장 안 함") { _, _ -> finish() }
                .setNeutralButton("취소", null)
                .show()
            return
        }
        finish()
    }

    @Deprecated("뒤로 가기 처리")
    override fun onBackPressed() {
        handleBack()
    }

    override fun onDestroy() {
        buildToken++
        main.removeCallbacksAndMessages(null)
        io.shutdownNow()
        imageIo.shutdownNow()
        super.onDestroy()
    }

    // ---------------------------------------------------------------- 메뉴

    private fun showMenu(anchor: View) {
        val m = model ?: return
        val menu = PopupMenu(this, anchor)
        menu.menu.add(0, 1, 0, "다른 이름으로 저장")
        if (editMode) menu.menu.add(0, 2, 1, "찾기")
        menu.menu.add(0, 3, 2, "글자 크기")
        if (uri != null) menu.menu.add(0, 4, 3, "공유")
        menu.menu.add(0, 5, 4, "문서 정보")
        menu.menu.add(0, 6, 5, "앱 정보")
        menu.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                1 -> save(saveAs = true, thenFinish = false)
                2 -> openFind()
                3 -> chooseTextSize()
                4 -> share()
                5 -> showInfo(m)
                6 -> startActivity(Intent(this, AboutActivity::class.java))
            }
            true
        }
        menu.show()
    }

    private fun chooseTextSize() {
        val labels = arrayOf("작게", "보통", "크게", "아주 크게")
        val values = floatArrayOf(1.2f, 1.5f, 1.8f, 2.2f)
        val current = Prefs.textScale(this)
        val checked = values.indices.minByOrNull { abs(values[it] - current) } ?: 1
        AlertDialog.Builder(this)
            .setTitle("글자 크기")
            .setSingleChoiceItems(labels, checked) { dialog, which ->
                dialog.dismiss()
                applyTextScale(current, values[which])
            }
            .setNegativeButton("취소", null)
            .show()
    }

    /** 이미 만든 입력칸의 글자 크기·들여쓰기를 비율대로 바꾼다(고친 내용은 그대로). */
    private fun applyTextScale(old: Float, new: Float) {
        if (old == new) return
        Prefs.setTextScale(this, new)
        val k = new / old
        for (f in flows) {
            val e = f.text ?: continue
            for (s in e.getSpans(0, e.length, AbsoluteSizeSpan::class.java)) {
                val st = e.getSpanStart(s)
                val en = e.getSpanEnd(s)
                val fl = e.getSpanFlags(s)
                e.removeSpan(s)
                e.setSpan(AbsoluteSizeSpan((s.size * k).roundToInt(), s.dip), st, en, fl)
            }
            for (s in e.getSpans(0, e.length, LeadingMarginSpan.Standard::class.java)) {
                val st = e.getSpanStart(s)
                val en = e.getSpanEnd(s)
                val fl = e.getSpanFlags(s)
                e.removeSpan(s)
                val first = s.getLeadingMargin(true)
                val rest = s.getLeadingMargin(false)
                e.setSpan(LeadingMarginSpan.Standard((first * k).roundToInt(), (rest * k).roundToInt()), st, en, fl)
            }
            f.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX, f.textSize * k)
        }
    }

    private fun share() {
        val target = uri ?: return
        if (collectEdits().isNotEmpty()) toast("저장한 내용까지만 공유돼요.")
        val m = model ?: return
        val send = Intent(Intent.ACTION_SEND).apply {
            type = m.format.mimeType
            putExtra(Intent.EXTRA_STREAM, target)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            startActivity(Intent.createChooser(send, "문서 공유"))
        } catch (e: Exception) {
            toast("공유할 앱이 없어요.")
        }
    }

    private fun showInfo(m: DocModel) {
        var tables = 0
        var images = 0
        var boxes = 0
        var objects = 0
        fun walk(blocks: List<kr.naya.hwpedit.core.Block>) {
            for (b in blocks) when (b) {
                is TableBlock -> {
                    tables++; b.cells.forEach { walk(it.blocks) }; walk(b.caption)
                }
                is ImageBlock -> {
                    images++; walk(b.caption)
                }
                is BoxBlock -> {
                    boxes++; walk(b.blocks)
                }
                is ObjectBlock -> objects++
                else -> {}
            }
        }
        walk(m.blocks)
        val paragraphs = m.allFlows().sumOf { it.paragraphs.size }
        val chars = m.allFlows().sumOf { it.text.length }
        val size = original?.size ?: 0
        val text = buildString {
            append("형식: ").append(m.format.extension.uppercase()).append('\n')
            append("크기: ").append(String.format("%.1f", size / 1024.0)).append(" KB\n")
            append("문단: ").append(paragraphs).append("개, 글자: ").append(chars).append("자\n")
            append("표: ").append(tables).append("개, 그림: ").append(images).append("개\n")
            append("글상자·머리말·각주 등: ").append(boxes).append("개\n")
            if (objects > 0) append("미리 볼 수 없는 개체(수식·도형 등): ").append(objects).append("개\n")
            m.readOnlyReason?.let { append('\n').append(it).append('\n') }
            append("\n화면은 휴대폰에서 읽기 좋게 글을 다시 배치한 모양이에요. 실제 쪽 모양은 한글에서 확인해 주세요.")
        }
        AlertDialog.Builder(this).setTitle(displayName).setMessage(text).setPositiveButton("확인", null).show()
    }

    // ---------------------------------------------------------------- 찾기

    private fun openFind() {
        if (model == null) return
        findBar.visibility = View.VISIBLE
        findInput.requestFocus()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager)
            ?.showSoftInput(findInput, InputMethodManager.SHOW_IMPLICIT)
        if (findInput.text.isNotEmpty()) runFind()
    }

    private fun closeFind() {
        if (findBar.visibility != View.VISIBLE) return
        findBar.visibility = View.GONE
        for (f in flows) f.clearFindMarks()
        matches = emptyList()
        currentMatch = -1
        hideKeyboard()
    }

    private fun runFind() {
        for (f in flows) f.clearFindMarks()
        val q = findInput.text.toString()
        val found = ArrayList<Match>()
        if (q.isNotEmpty()) {
            for (f in flows) {
                val e = f.text ?: continue
                for (start in DocText.findAll(e, q)) {
                    found.add(Match(f, start))
                    e.setSpan(FindSpan(Palette.FIND), start, start + q.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
        }
        matches = found
        currentMatch = -1
        if (found.isEmpty()) {
            findCount.text = if (q.isEmpty()) "" else "없음"
        } else {
            moveMatch(+1)
        }
    }

    private fun moveMatch(delta: Int) {
        if (matches.isEmpty()) return
        val q = findInput.text.toString()
        matches.getOrNull(currentMatch)?.let { old ->
            val e = old.flow.text
            for (s in e.getSpans(old.start, old.start + q.length, FindSpan::class.java)) e.removeSpan(s)
            if (old.start + q.length <= e.length) {
                e.setSpan(FindSpan(Palette.FIND), old.start, old.start + q.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
        }
        currentMatch = (currentMatch + delta + matches.size) % matches.size
        val mm = matches[currentMatch]
        val e = mm.flow.text
        if (mm.start + q.length <= e.length) {
            for (s in e.getSpans(mm.start, mm.start + q.length, FindSpan::class.java)) e.removeSpan(s)
            e.setSpan(FindSpan(Palette.FIND_CURRENT), mm.start, mm.start + q.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        findCount.text = "${currentMatch + 1}/${matches.size}"
        scrollToOffset(mm.flow, mm.start)
    }

    private fun scrollToOffset(view: FlowEditText, offset: Int) {
        val layout = view.layout
        if (layout == null) {
            view.post { scrollToOffset(view, offset) }
            return
        }
        var y = layout.getLineTop(layout.getLineForOffset(offset.coerceIn(0, view.text.length))) + view.paddingTop
        var v: View = view
        val content = scroll.getChildAt(0)
        while (v !== content) {
            y += v.top
            v = v.parent as? View ?: break
        }
        scroll.smoothScrollTo(0, max(0, y - scroll.height / 3))
    }

    // ---------------------------------------------------------------- 기타

    private fun showOverlay(text: String) {
        overlayText.text = text
        overlay.visibility = View.VISIBLE
    }

    private fun hideOverlay() {
        overlay.visibility = View.GONE
    }

    private fun toast(text: String) = Toast.makeText(this, text, Toast.LENGTH_LONG).show()

    /** 시험용: 지금 보이는 입력칸들. */
    internal fun flowViews(): List<FlowEditText> = flows

    internal fun isBusyForTest(): Boolean = busy || building || overlay.visibility == View.VISIBLE

    internal fun setEditModeForTest(on: Boolean) = setEditMode(on)

    internal fun saveForTest() = save(saveAs = false, thenFinish = false)

    companion object {
        const val EXTRA_NEW = "new_document"
        private const val REQ_SAVE_AS = 2
        private const val PAGE_MARGIN_DP = 6
        private const val PAGE_PADDING_DP = 16
    }
}
