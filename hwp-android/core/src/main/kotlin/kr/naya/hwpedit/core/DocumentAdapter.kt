package kr.naya.hwpedit.core

import kr.naya.hwpedit.core.edit.Anchor
import kr.naya.hwpedit.core.edit.FlowRebuilder
import kr.naya.hwpedit.core.edit.RebuiltPara
import kr.naya.hwpedit.core.edit.SourcePara
import java.util.IdentityHashMap

/**
 * hwp·hwpx 공통 뼈대.
 *
 * 문서를 훑으며 문단을 글 흐름(TextFlowBlock)으로 묶고, 각 흐름이 어느 문단 목록의
 * 몇 번째부터 몇 개인지 기억해 둔다(FlowBinding). 저장할 때는 고친 흐름만 다시 만든다.
 *
 * @param P 문단 객체 형식
 * @param C 문단 목록(구역, 표 칸, 글상자 등) 형식
 */
internal abstract class DocumentAdapter<P : Any, C : Any> {

    class FlowBinding(val container: Any, val start: Int, val count: Int, val sources: List<SourcePara>)

    private val bindings = ArrayList<FlowBinding>()

    /** 훑은 문단에 들어 있던 보이지 않는 개체 수(시험용). */
    var anchorsSeen = 0
        private set
    private val charStyleCache = HashMap<String, CharStyle>()
    protected val warnings = LinkedHashSet<String>()

    // ---- 형식마다 구현할 부분 ----
    protected abstract fun paragraphs(container: C): List<P>
    protected abstract fun replace(container: C, start: Int, count: Int, newParas: List<P>)
    protected abstract fun read(p: P): SourcePara
    protected abstract fun write(r: RebuiltPara): P
    protected abstract fun paraStyle(p: P): ParaStyle
    protected abstract fun charStyle(fmt: String): CharStyle

    /** 문단 앞에 보여 줄 개체(머리말·꼬리말). 없으면 빈 목록. */
    protected abstract fun leadingBlocks(anchor: Anchor): List<Block>

    /** 문단 뒤에 따로 보여 줄 개체(표, 그림, 글상자, 각주 등). 해당 없으면 null. */
    protected abstract fun trailingBlocks(anchor: Anchor): List<Block>?

    // ---- 공통 동작 ----

    /** 문단 목록 하나를 화면 블록으로 바꾼다. 표 칸 등 안쪽 목록도 이 함수로 처리한다. */
    protected fun walk(container: C): List<Block> {
        val paras = paragraphs(container)
        val out = ArrayList<Block>()
        var flowStart = -1
        val flowSources = ArrayList<SourcePara>()
        val flowViews = ArrayList<ParaView>()
        var flowChars = 0

        fun closeFlow() {
            if (flowSources.isEmpty()) return
            val id = bindings.size
            bindings.add(FlowBinding(container, flowStart, flowSources.size, ArrayList(flowSources)))
            out.add(TextFlowBlock(id, ArrayList(flowViews)))
            flowSources.clear()
            flowViews.clear()
            flowChars = 0
            flowStart = -1
        }

        fun addToFlow(index: Int, sp: SourcePara, p: P) {
            if (flowSources.isEmpty()) flowStart = index
            flowSources.add(sp)
            flowViews.add(viewOf(sp, p))
            flowChars += sp.text.length + 1
        }

        for ((index, p) in paras.withIndex()) {
            val sp = read(p)
            anchorsSeen += sp.anchors.size
            val leading = ArrayList<Block>()
            val trailing = ArrayList<Block>()
            var breaksAfter = false
            for (a in sp.anchors) {
                leading.addAll(leadingBlocks(a))
                val t = trailingBlocks(a)
                if (t != null) {
                    trailing.addAll(t)
                    breaksAfter = true
                }
            }
            if (leading.isNotEmpty()) {
                closeFlow()
                out.addAll(leading)
            }
            if (!breaksAfter) {
                addToFlow(index, sp, p)
                // 입력칸 하나가 너무 커지면 휴대폰에서 느려지므로 적당히 끊는다.
                if (flowSources.size >= MAX_FLOW_PARAGRAPHS || flowChars >= MAX_FLOW_CHARS) closeFlow()
            } else {
                if (sp.text.isNotEmpty()) addToFlow(index, sp, p)
                closeFlow()
                out.addAll(trailing)
            }
        }
        closeFlow()
        return out
    }

    private fun viewOf(sp: SourcePara, p: P): ParaView {
        val runs = ArrayList<StyledRun>()
        var start = 0
        for (i in 1..sp.text.length) {
            if (i == sp.text.length || sp.fmts[i] != sp.fmts[start]) {
                runs.add(StyledRun(start, i, styleOf(sp.fmts[start])))
                start = i
            }
        }
        val style = try {
            paraStyle(p)
        } catch (e: RuntimeException) {
            ParaStyle.DEFAULT
        }
        return ParaView(sp.text, runs, style)
    }

    private fun styleOf(fmt: String): CharStyle = charStyleCache.getOrPut(fmt) {
        try {
            charStyle(fmt)
        } catch (e: RuntimeException) {
            CharStyle.DEFAULT
        }
    }

    /** 고친 흐름을 문서 객체에 반영한다. edits: flowId -> 새 글(문단은 \n 으로 구분). */
    fun applyEdits(edits: Map<Int, String>) {
        val byContainer = IdentityHashMap<Any, MutableList<Pair<FlowBinding, String>>>()
        for ((flowId, raw) in edits) {
            val b = bindings.getOrNull(flowId) ?: throw IllegalArgumentException("알 수 없는 글 흐름: $flowId")
            val text = SpecialChars.sanitize(raw)
            if (text == b.sources.joinToString("\n") { it.text }) continue
            byContainer.getOrPut(b.container) { ArrayList() }.add(b to text)
        }
        for ((container, list) in byContainer) {
            // 뒤쪽 흐름부터 바꿔야 앞쪽 흐름의 문단 번호가 흔들리지 않는다.
            list.sortByDescending { it.first.start }
            for ((b, text) in list) {
                val rebuilt = FlowRebuilder.rebuild(b.sources, text)
                // 새로 만드는 문단을 먼저 만들고, 원래 문단을 고친다.
                val result = arrayOfNulls<Any>(rebuilt.size)
                for ((i, r) in rebuilt.withIndex()) if (!r.reuse) result[i] = write(r)
                for ((i, r) in rebuilt.withIndex()) if (r.reuse) {
                    result[i] = if (r.unchanged) r.template.ref else write(r)
                }
                @Suppress("UNCHECKED_CAST")
                replace(container as C, b.start, b.count, result.map { it as P })
            }
        }
    }

    companion object {
        const val MAX_FLOW_PARAGRAPHS = 80
        const val MAX_FLOW_CHARS = 8000
    }
}
