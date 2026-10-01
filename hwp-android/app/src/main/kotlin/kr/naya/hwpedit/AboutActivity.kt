package kr.naya.hwpedit

import android.app.Activity
import android.os.Bundle
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import kr.naya.hwpedit.ui.EdgeToEdge
import kr.naya.hwpedit.ui.Palette
import kr.naya.hwpedit.ui.TopBar
import kr.naya.hwpedit.ui.divider
import kr.naya.hwpedit.ui.dp
import kr.naya.hwpedit.ui.iconButton
import kr.naya.hwpedit.ui.label

/** 앱 정보와 오픈소스 라이선스. */
class AboutActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        EdgeToEdge.enable(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Palette.SURFACE)
        }
        val bar = TopBar(this).apply {
            setLeading(iconButton(R.drawable.ic_back, "뒤로") { finish() })
            title.text = "앱 정보"
        }
        root.addView(bar)
        root.addView(divider())
        val scroll = ScrollView(this).apply { clipToPadding = false }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(16), dp(20), dp(24))
        }
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        val version = try {
            packageManager.getPackageInfo(packageName, 0).versionName
        } catch (e: Exception) {
            "?"
        }
        fun heading(t: String) = content.addView(label(t, 17f, Palette.TEXT, bold = true).apply { setPadding(0, dp(20), 0, dp(6)) })
        fun para(t: String) = content.addView(label(t, 14f, Palette.SUBTEXT).apply { setLineSpacing(0f, 1.25f) })

        content.addView(label(getString(R.string.app_name), 24f, Palette.TEXT, bold = true))
        para("버전 $version")

        heading("할 수 있는 것")
        para("• hwp(한글 5.0 이후), hwpx 문서 열기\n• 본문·표 칸·글상자·머리말·각주의 글 고치기\n• 고치지 않은 부분과 글자 모양은 원래대로 두고 저장\n• 저장한 뒤 다시 읽어서 글이 제대로 들어갔는지 확인\n• 찾기, 되돌리기, 글자 크기 바꾸기, 다른 이름으로 저장")

        heading("아직 못 하는 것")
        para("• 굵게·색 같은 글자 모양 바꾸기, 표·그림 넣거나 지우기\n• 한글과 똑같은 쪽 모양 보기(휴대폰에 맞게 글을 다시 배치해 보여 줘요)\n• 암호가 걸린 문서, 배포용 문서 저장, 한글 97 이전 형식")

        heading("오픈소스")
        para("이 앱은 다음 오픈소스를 사용해요.\n\n" +
            "• hwplib — Apache License 2.0\n  https://github.com/neolord0/hwplib\n\n" +
            "• hwpxlib — Apache License 2.0\n  https://github.com/neolord0/hwpxlib\n\n" +
            "• Material Icons — Apache License 2.0\n  https://github.com/google/material-design-icons")
        heading("알림")
        para("본 제품은 한글과컴퓨터의 한/글 문서 파일(.hwp) 공개 문서를 참고하여 개발하였습니다.\n" +
            "'한글', '한컴'은 주식회사 한글과컴퓨터의 상표이며, 이 앱은 한글과컴퓨터와 관계가 없어요.")

        setContentView(root)
        EdgeToEdge.apply(root, bar, scroll)
    }
}
