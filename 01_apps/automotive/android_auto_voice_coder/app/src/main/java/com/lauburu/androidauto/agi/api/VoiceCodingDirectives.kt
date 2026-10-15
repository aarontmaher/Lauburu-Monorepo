package com.lauburu.androidauto.agi.api

/**
 * Enumeration of the 5 core hands-free voice coding directives supported by the AGI agent,
 * along with UNKNOWN fallback.
 */
enum class VoiceDirective(
    val token: String,
    val actionIntent: String,
    val displayName: String,
    val defaultDescription: String
) {
    EXPLAIN_DIFF(
        token = "EXPLAIN_DIFF",
        actionIntent = "EXPLAIN_GIT_DIFF",
        displayName = "Explain Diff",
        defaultDescription = "Explain changes in active repository or file"
    ),
    RUN_TESTS(
        token = "RUN_TESTS",
        actionIntent = "RUN_VERIFICATION_TESTS",
        displayName = "Run Tests",
        defaultDescription = "Execute verification test suite across mesh"
    ),
    REFACTOR(
        token = "REFACTOR",
        actionIntent = "DRAFT_FUNCTION_REFACTOR",
        displayName = "Refactor Function",
        defaultDescription = "Request targeted AST code refactoring"
    ),
    GIT_STATUS(
        token = "GIT_STATUS",
        actionIntent = "QUERY_GIT_STATUS",
        displayName = "Show Git Status",
        defaultDescription = "Inspect branch status and modified files"
    ),
    COMMIT(
        token = "COMMIT",
        actionIntent = "CONFIRM_GIT_COMMIT",
        displayName = "Commit Changes",
        defaultDescription = "Approve and commit drafted code changes"
    ),
    REGION_BACKSPACE(
        token = "REGION_BACKSPACE",
        actionIntent = "AST_SCOPE_BACKSPACE",
        displayName = "Backspace Region",
        defaultDescription = "Delete active function, block, or statement scope via AST slicing"
    ),
    UNDO_LAST_ACTION(
        token = "UNDO_LAST_ACTION",
        actionIntent = "AST_SCOPE_REWIND",
        displayName = "Undo Action",
        defaultDescription = "Rewind code to previous AST snapshot in undo history stack"
    ),
    UNKNOWN(
        token = "UNKNOWN",
        actionIntent = "GENERAL_PAIR_PROGRAMMING_QUERY",
        displayName = "General Query",
        defaultDescription = "Unhandled or conversational voice directive"
    );

    companion object {
        // Aliases for alternative naming conventions
        val EXPLAIN_GIT_DIFF = EXPLAIN_DIFF
        val RUN_VERIFICATION_TESTS = RUN_TESTS
        val DRAFT_FUNCTION_REFACTOR = REFACTOR
        val QUERY_GIT_STATUS = GIT_STATUS
        val CONFIRM_GIT_COMMIT = COMMIT

        /**
         * Resolves a directive token or intent string to the corresponding VoiceDirective enum.
         */
        fun fromToken(token: String?): VoiceDirective {
            if (token.isNullOrBlank()) return UNKNOWN
            return entries.firstOrNull {
                it.token.equals(token, ignoreCase = true) ||
                it.actionIntent.equals(token, ignoreCase = true) ||
                it.name.equals(token, ignoreCase = true)
            } ?: UNKNOWN
        }
    }
}

/**
 * Structured model representing the output of the Natural Language Directive Parser.
 */
data class ParsedVoiceDirective(
    val directive: VoiceDirective,
    val action: String = directive.token,
    val actionIntent: String = directive.actionIntent,
    val target: String = "",
    val rawTranscript: String = ""
)

/**
 * Natural Language Parser / Directive Resolver mapping spoken voice transcripts into
 * structured VoiceDirective actions and extracted parameter targets.
 */
object VoiceDirectiveParser {

    private val FILLER_WORDS_REGEX = Regex("\\b(uh|um|please|could you|can you|hey agent)\\b", RegexOption.IGNORE_CASE)
    private val PUNCTUATION_REGEX = Regex("[!?,.:;]")
    private val NEGATIVE_COMMAND_REGEX = Regex(
        "(?:^(?:do\\s+not|don'?t|dont|cancel|abort|stop|never|discard|reject)\\b)|(?:\\b(?:do\\s+not|don'?t|dont|cancel|abort|stop|never)\\s+(?:commit|run|test|refactor|diff|explain|show|status|changes|verification)\\b)",
        RegexOption.IGNORE_CASE
    )

    /**
     * Cleans spoken transcript by removing noise, verbal filler words, and punctuation.
     */
    fun cleanTranscript(rawTranscript: String?): String {
        if (rawTranscript.isNullOrBlank()) return ""
        val withoutPunctuation = PUNCTUATION_REGEX.replace(rawTranscript, "")
        val withoutFillers = FILLER_WORDS_REGEX.replace(withoutPunctuation, " ")
        return withoutFillers.trim().replace(Regex("\\s+"), " ")
    }

    /**
     * Parses a spoken transcript into a ParsedVoiceDirective.
     */
    fun parse(transcript: String?): ParsedVoiceDirective {
        val raw = transcript ?: ""
        if (raw.isBlank()) {
            return ParsedVoiceDirective(
                directive = VoiceDirective.UNKNOWN,
                target = "",
                rawTranscript = raw
            )
        }

        val clean = cleanTranscript(raw).lowercase()

        // Reject negative or abort commands from inadvertently matching positive action keywords
        if (NEGATIVE_COMMAND_REGEX.containsMatchIn(clean)) {
            return ParsedVoiceDirective(
                directive = VoiceDirective.UNKNOWN,
                target = "",
                rawTranscript = raw
            )
        }

        // 1. EXPLAIN_DIFF
        val explainKeywords = listOf("explain diff", "explain changes", "what changed", "show diff", "diff")
        if (explainKeywords.any { clean.contains(it) }) {
            var target = ""
            val targetMatch = Regex("(?:in|for)\\s+([a-zA-Z0-9_\\-/. ]+)").find(clean)
            if (targetMatch != null) {
                target = targetMatch.groupValues[1].trim()
            }
            return ParsedVoiceDirective(
                directive = VoiceDirective.EXPLAIN_DIFF,
                target = target,
                rawTranscript = raw
            )
        }

        // 2. RUN_TESTS
        val testKeywords = listOf("run tests", "verify suite", "execute test", "run verification", "test")
        if (testKeywords.any { clean.contains(it) }) {
            var target = "all"
            val targetMatch = Regex("(?:on|for)\\s+([a-zA-Z0-9_\\-/. ]+)").find(clean)
            if (targetMatch != null) {
                target = targetMatch.groupValues[1].trim()
            }
            return ParsedVoiceDirective(
                directive = VoiceDirective.RUN_TESTS,
                target = target,
                rawTranscript = raw
            )
        }

        // 3. REFACTOR
        val refactorKeywords = listOf("refactor function", "refactor", "rewrite")
        if (refactorKeywords.any { clean.contains(it) }) {
            var target = ""
            // Use regex on raw or cleaned to preserve special code tokens like <T>, ($id: Int)
            val refactorMatch = Regex("refactor\\s+(?:function\\s+)?([a-zA-Z0-9_\\-/. \$<>()]+)", RegexOption.IGNORE_CASE).find(raw)
            if (refactorMatch != null) {
                target = refactorMatch.groupValues[1].trim()
            }
            return ParsedVoiceDirective(
                directive = VoiceDirective.REFACTOR,
                target = target,
                rawTranscript = raw
            )
        }

        // 4. GIT_STATUS
        val statusKeywords = listOf("show git status", "git status", "status of branch", "branch status", "status")
        if (statusKeywords.any { clean.contains(it) }) {
            return ParsedVoiceDirective(
                directive = VoiceDirective.GIT_STATUS,
                target = "",
                rawTranscript = raw
            )
        }

        // 5. COMMIT
        val commitKeywords = listOf("commit changes", "confirm commit", "approve and commit", "commit")
        if (commitKeywords.any { clean.contains(it) }) {
            var msg = ""
            val commitMatch = Regex("commit(?:\\s+changes)?(?:\\s+with\\s+message\\s+)?(.*)", RegexOption.IGNORE_CASE).find(clean)
            if (commitMatch != null) {
                msg = commitMatch.groupValues[1].trim()
            }
            return ParsedVoiceDirective(
                directive = VoiceDirective.COMMIT,
                target = msg,
                rawTranscript = raw
            )
        }

        // Default UNKNOWN
        return ParsedVoiceDirective(
            directive = VoiceDirective.UNKNOWN,
            target = "",
            rawTranscript = raw
        )
    }
}
