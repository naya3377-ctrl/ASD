package kr.naya.hwpedit.core.edit

/**
 * 두 순서열에서 그대로 남은 항목의 짝(가장 긴 공통 부분열)을 찾는다.
 * Myers 차이 알고리즘. 앞뒤 공통 부분을 먼저 걷어 내고 가운데만 비교한다.
 */
object TextDiff {
    /** 가운데 비교에서 허용하는 최대 편집 거리. 넘으면 가운데를 통째로 바뀐 것으로 본다. */
    private const val MAX_EDIT_DISTANCE = 1500

    /**
     * 짝지어진 (oldIndex, newIndex) 목록을 순서대로 돌려준다.
     * 결과는 [old0, new0, old1, new1, ...] 형태의 IntArray.
     */
    fun matches(oldSize: Int, newSize: Int, equal: (Int, Int) -> Boolean): IntArray {
        var prefix = 0
        while (prefix < oldSize && prefix < newSize && equal(prefix, prefix)) prefix++
        var suffix = 0
        while (suffix < oldSize - prefix && suffix < newSize - prefix &&
            equal(oldSize - 1 - suffix, newSize - 1 - suffix)
        ) suffix++

        val out = IntArrayBuilder()
        for (i in 0 until prefix) out.add(i, i)

        val aStart = prefix
        val bStart = prefix
        val n = oldSize - prefix - suffix
        val m = newSize - prefix - suffix
        if (n > 0 && m > 0) {
            myers(n, m, { i, j -> equal(aStart + i, bStart + j) }) { i, j ->
                out.add(aStart + i, bStart + j)
            }
        }

        for (k in 0 until suffix) out.add(oldSize - suffix + k, newSize - suffix + k)
        return out.toArray()
    }

    fun matches(old: CharSequence, new: CharSequence): IntArray =
        matches(old.length, new.length) { i, j -> old[i] == new[j] }

    fun matches(old: List<String>, new: List<String>): IntArray {
        val oh = IntArray(old.size) { old[it].hashCode() }
        val nh = IntArray(new.size) { new[it].hashCode() }
        return matches(old.size, new.size) { i, j -> oh[i] == nh[j] && old[i] == new[j] }
    }

    private fun myers(
        n: Int,
        m: Int,
        equal: (Int, Int) -> Boolean,
        emit: (Int, Int) -> Unit,
    ) {
        val max = n + m
        val offset = max
        val v = IntArray(2 * max + 2)
        // d 단계마다 v[-d..d] 를 저장해 두었다가 거꾸로 따라간다.
        val trace = ArrayList<IntArray>()
        var found = false
        var dFound = 0
        outer@ for (d in 0..minOf(max, MAX_EDIT_DISTANCE)) {
            val snapshot = IntArray(2 * d + 1)
            var k = -d
            while (k <= d) {
                var x = if (k == -d || (k != d && v[offset + k - 1] < v[offset + k + 1])) {
                    v[offset + k + 1]
                } else {
                    v[offset + k - 1] + 1
                }
                var y = x - k
                while (x < n && y < m && equal(x, y)) {
                    x++; y++
                }
                v[offset + k] = x
                snapshot[k + d] = x
                if (x >= n && y >= m) {
                    trace.add(snapshot)
                    found = true
                    dFound = d
                    break@outer
                }
                k += 2
            }
            trace.add(snapshot)
        }
        if (!found) return // 너무 많이 바뀜: 공통 부분 없음으로 처리

        // 거꾸로 따라가며 대각선 이동(같은 글자)을 모은다.
        val pairs = IntArrayBuilder()
        var x = n
        var y = m
        for (d in dFound downTo 1) {
            val prev = trace[d - 1]
            val k = x - y
            val base = d - 1
            val prevK = if (k == -d || (k != d && prev[k - 1 + base] < prev[k + 1 + base])) k + 1 else k - 1
            val prevX = prev[prevK + base]
            val prevY = prevX - prevK
            while (x > prevX && y > prevY) {
                x--; y--
                pairs.add(x, y)
            }
            x = prevX
            y = prevY
        }
        while (x > 0 && y > 0) {
            x--; y--
            pairs.add(x, y)
        }
        val arr = pairs.toArray()
        var i = arr.size - 2
        while (i >= 0) {
            emit(arr[i], arr[i + 1])
            i -= 2
        }
    }

    private class IntArrayBuilder {
        private var data = IntArray(64)
        private var size = 0
        fun add(a: Int, b: Int) {
            if (size + 2 > data.size) data = data.copyOf(data.size * 2)
            data[size++] = a
            data[size++] = b
        }
        fun toArray(): IntArray = data.copyOf(size)
    }
}

/**
 * 짝 목록으로 만든 위치 대응표.
 * newToOld[j] = 새 글의 j번째 글자가 원래 몇 번째 글자였는지(새로 넣은 글자는 -1).
 * oldPosToNew[p] = 원래 글의 p 위치(글자 사이)가 새 글에서 어디인지. 지운 곳·넣은 곳에서는 앞쪽에 붙는다.
 */
class PositionMap(oldSize: Int, newSize: Int, matches: IntArray) {
    val newToOld = IntArray(newSize) { -1 }
    val oldToNew = IntArray(oldSize) { -1 }
    val oldPosToNew = IntArray(oldSize + 1)

    init {
        var i = 0
        while (i < matches.size) {
            newToOld[matches[i + 1]] = matches[i]
            oldToNew[matches[i]] = matches[i + 1]
            i += 2
        }
        var lastNew = -1
        oldPosToNew[0] = 0
        for (p in 1..oldSize) {
            val j = oldToNew[p - 1]
            if (j >= 0) lastNew = j
            oldPosToNew[p] = lastNew + 1
        }
    }

    private val newSize = newSize

    /**
     * 원래 위치 p 를 새 위치로 옮긴다.
     * rightBias 면, p 바로 뒤 글자가 남아 있을 때 그 글자 바로 앞(그 사이에 넣은 글 뒤)으로 옮긴다.
     * 범위 끝 표시를 범위 끝에 덧붙인 글 뒤에 두기 위해서다.
     */
    fun map(p: Int, rightBias: Boolean): Int {
        if (!rightBias) return oldPosToNew[p]
        if (p >= oldToNew.size) return newSize
        val j = oldToNew[p]
        return if (j >= 0) j else oldPosToNew[p]
    }
}
