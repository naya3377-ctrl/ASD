package kr.naya.hwpedit.core

import org.junit.Test

/** 시험 문서를 열어 모델을 출력한다(눈으로 확인하는 용도). */
class DumpSamplesTest {
    @Test
    fun dumpAll() {
        val sb = StringBuilder()
        for (name in TestSupport.sampleNames) {
            sb.append("===== ").append(name).append('\n')
            val doc = HwpDocuments.open(TestSupport.sample(name))
            sb.append(TestSupport.dump(doc.model))
        }
        TestSupport.output("dump.txt", sb.toString().toByteArray())
        println(sb)
    }
}
