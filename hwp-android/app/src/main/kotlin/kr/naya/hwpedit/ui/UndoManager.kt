package kr.naya.hwpedit.ui

import android.content.Context
import android.os.SystemClock
import android.text.Editable
import android.text.TextWatcher
import android.view.inputmethod.InputMethodManager
import android.widget.EditText

/**
 * 여러 입력칸에 걸친 되돌리기/다시 하기.
 * 연달아 친 글자(한글 조합 포함)와 연달아 지운 글자는 한 번에 되돌린다.
 */
class UndoManager(private val onChange: () -> Unit) {

    private class Step(val view: EditText, var start: Int, var before: String, var after: String, var time: Long)

    private val undoStack = ArrayDeque<Step>()
    private val redoStack = ArrayDeque<Step>()
    private var applying = false

    val canUndo: Boolean get() = undoStack.isNotEmpty()
    val canRedo: Boolean get() = redoStack.isNotEmpty()

    fun watch(view: EditText) {
        view.addTextChangedListener(object : TextWatcher {
            private var removed = ""

            override fun beforeTextChanged(s: CharSequence, start: Int, count: Int, after: Int) {
                if (!applying) removed = s.subSequence(start, start + count).toString()
            }

            override fun onTextChanged(s: CharSequence, start: Int, before: Int, count: Int) {
                if (applying) return
                record(view, start, removed, s.subSequence(start, start + count).toString())
            }

            override fun afterTextChanged(s: Editable) {}
        })
    }

    fun clear() {
        undoStack.clear()
        redoStack.clear()
        onChange()
    }

    private fun record(view: EditText, start: Int, before: String, after: String) {
        if (before == after) return
        redoStack.clear()
        val now = SystemClock.uptimeMillis()
        val last = undoStack.lastOrNull()
        if (last != null && last.view === view && now - last.time < MERGE_WINDOW_MS) {
            val lastEnd = last.start + last.after.length
            when {
                // 이어서 입력하거나, 방금 입력한 글자 끝부분을 바꿈(한글 조합)
                start >= last.start && start + before.length == lastEnd && start - last.start <= last.after.length -> {
                    last.after = last.after.substring(0, start - last.start) + after
                    last.time = now
                    onChange()
                    return
                }
                // 뒤로 지우기를 이어서
                after.isEmpty() && last.after.isEmpty() && start + before.length == last.start -> {
                    last.before = before + last.before
                    last.start = start
                    last.time = now
                    onChange()
                    return
                }
            }
        }
        undoStack.addLast(Step(view, start, before, after, now))
        while (undoStack.size > MAX_STEPS) undoStack.removeFirst()
        onChange()
    }

    fun undo() {
        val step = undoStack.removeLastOrNull() ?: return
        apply(step.view, step.start, step.after.length, step.before)
        redoStack.addLast(step)
        onChange()
    }

    fun redo() {
        val step = redoStack.removeLastOrNull() ?: return
        apply(step.view, step.start, step.before.length, step.after)
        undoStack.addLast(step)
        onChange()
    }

    private fun apply(view: EditText, start: Int, length: Int, replacement: String) {
        val text = view.text ?: return
        val s = start.coerceIn(0, text.length)
        val e = (start + length).coerceIn(s, text.length)
        applying = true
        try {
            text.replace(s, e, replacement)
            view.setSelection((s + replacement.length).coerceAtMost(view.text.length))
        } finally {
            applying = false
        }
        // 한글 조합 중이던 키보드 상태를 새로 고친다.
        (view.context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager)?.restartInput(view)
        view.requestFocus()
    }

    companion object {
        private const val MERGE_WINDOW_MS = 1500L
        private const val MAX_STEPS = 300
    }
}
