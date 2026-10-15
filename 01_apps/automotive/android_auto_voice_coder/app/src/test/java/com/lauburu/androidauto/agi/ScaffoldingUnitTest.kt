package com.lauburu.androidauto.agi

import com.lauburu.androidauto.agi.service.LauburuCarAppService
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class ScaffoldingUnitTest {

    @Test
    fun testServiceInstantiatesHostValidator() {
        val service = LauburuCarAppService()
        val validator = service.createHostValidator()
        assertNotNull(validator)
    }
}
