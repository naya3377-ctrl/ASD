package kr.naya.hwpedit

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.format.DateUtils
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Toast
import kr.naya.hwpedit.ui.EdgeToEdge
import kr.naya.hwpedit.ui.Palette
import kr.naya.hwpedit.ui.dp
import kr.naya.hwpedit.ui.label
import kr.naya.hwpedit.ui.pillButton
import kr.naya.hwpedit.ui.ripple

/** 시작 화면: 문서 열기, 새 문서, 최근 문서. */
class MainActivity : Activity() {

    private lateinit var recents: Recents
    private lateinit var recentList: LinearLayout
    private lateinit var recentTitle: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        EdgeToEdge.enable(this)
        recents = Recents(this)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Palette.SURFACE)
        }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(40), dp(24), dp(24))
        }
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        val logo = ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
        }
        content.addView(logo, LinearLayout.LayoutParams(dp(64), dp(64)))
        content.addView(label(getString(R.string.app_name), 30f, Palette.TEXT, bold = true).apply {
            setPadding(0, dp(16), 0, 0)
        })
        content.addView(label("hwp · hwpx 문서를 열어 읽고, 글을 고쳐 저장할 수 있어요.", 15f, Palette.SUBTEXT).apply {
            setPadding(0, dp(6), 0, dp(28))
        })

        content.addView(pillButton("문서 열기", primary = true) { openPicker() },
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        content.addView(pillButton("새 문서 만들기", primary = false) { newDocument() },
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                topMargin = dp(10)
            })

        recentTitle = label("최근 문서", 14f, Palette.SUBTEXT, bold = true).apply { setPadding(0, dp(36), 0, dp(8)) }
        content.addView(recentTitle)
        recentList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        content.addView(recentList)

        val spacer = View(this)
        content.addView(spacer, LinearLayout.LayoutParams(1, 0, 1f))
        content.addView(label("앱 정보 · 오픈소스 라이선스", 13f, Palette.SUBTEXT).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(24), 0, dp(8))
            setOnClickListener { startActivity(Intent(this@MainActivity, AboutActivity::class.java)) }
        })

        setContentView(root)
        EdgeToEdge.apply(root, content, content)
    }

    override fun onResume() {
        super.onResume()
        showRecents()
    }

    private fun showRecents() {
        recentList.removeAllViews()
        val items = recents.list()
        recentTitle.visibility = if (items.isEmpty()) View.GONE else View.VISIBLE
        for (item in items) {
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                minimumHeight = dp(60)
                setPadding(dp(4), dp(6), dp(4), dp(6))
                background = ripple(null, dp(10).toFloat())
                isClickable = true
                setOnClickListener { openRecent(item) }
                setOnLongClickListener {
                    AlertDialog.Builder(this@MainActivity)
                        .setMessage("'${item.name}'을(를) 최근 문서에서 뺄까요?\n(파일은 지워지지 않아요.)")
                        .setPositiveButton("빼기") { _, _ ->
                            recents.remove(item.uri)
                            showRecents()
                        }
                        .setNegativeButton("취소", null)
                        .show()
                    true
                }
            }
            val icon = ImageView(this).apply {
                setImageResource(R.drawable.ic_doc)
                imageTintList = android.content.res.ColorStateList.valueOf(
                    if (item.name.endsWith(".hwpx", ignoreCase = true)) 0xFF0B8043.toInt() else Palette.ACCENT,
                )
            }
            row.addView(icon, LinearLayout.LayoutParams(dp(32), dp(32)))
            val texts = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(12), 0, 0, 0)
            }
            texts.addView(label(item.name, 16f, Palette.TEXT).apply {
                maxLines = 1
                ellipsize = android.text.TextUtils.TruncateAt.MIDDLE
            })
            texts.addView(label(
                DateUtils.getRelativeTimeSpanString(item.time, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS),
                13f, Palette.SUBTEXT,
            ))
            row.addView(texts, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            recentList.addView(row)
        }
    }

    private fun openPicker() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            // hwp 의 형식 이름은 기기마다 달라서 모든 파일을 보여 주고, 연 뒤에 내용을 보고 판단한다.
            type = "*/*"
            addFlags(
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION,
            )
        }
        try {
            startActivityForResult(intent, REQ_OPEN)
        } catch (e: Exception) {
            Toast.makeText(this, "파일 선택 화면을 열 수 없어요.", Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Activity 기본 결과 처리")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_OPEN || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        if (Recents.keepPermission(this, uri, data.flags)) {
            recents.add(uri, Files.displayName(contentResolver, uri))
        }
        openEditor(uri)
    }

    private fun openRecent(item: RecentDoc) {
        if (!Recents.hasPermission(this, item.uri)) {
            Toast.makeText(this, "이 문서를 다시 열 권한이 없어요. '문서 열기'로 다시 골라 주세요.", Toast.LENGTH_LONG).show()
            recents.remove(item.uri)
            showRecents()
            return
        }
        recents.add(item.uri, item.name)
        openEditor(item.uri)
    }

    private fun openEditor(uri: Uri) {
        val intent = Intent(this, EditorActivity::class.java).apply {
            action = Intent.ACTION_EDIT
            data = uri
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        }
        startActivity(intent)
    }

    private fun newDocument() {
        startActivity(Intent(this, EditorActivity::class.java).putExtra(EditorActivity.EXTRA_NEW, true))
    }

    companion object {
        private const val REQ_OPEN = 1
    }
}
