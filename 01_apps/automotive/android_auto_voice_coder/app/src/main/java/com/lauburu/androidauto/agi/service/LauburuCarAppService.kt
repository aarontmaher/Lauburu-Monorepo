package com.lauburu.androidauto.agi.service

import androidx.car.app.CarAppService
import androidx.car.app.Session
import androidx.car.app.SessionInfo
import androidx.car.app.validation.HostValidator

/**
 * Android Auto entrypoint service for Lauburu AGI Hands-Free Coding Agent.
 * Validates automotive hosts and initializes the in-cabin coding session.
 */
class LauburuCarAppService : CarAppService() {

    override fun createHostValidator(): HostValidator {
        return HostValidator.ALLOW_ALL_HOSTS_VALIDATOR
    }

    override fun onCreateSession(sessionInfo: SessionInfo): Session {
        return VoiceCodingSession()
    }
}
