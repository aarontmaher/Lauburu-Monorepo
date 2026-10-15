package com.lauburu.movesense

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.util.Log
import java.util.UUID

class BluetoothBridge(private val context: Context) {
    private val TAG = "MovesenseLauburuBLE"
    
    // Standard GATT Service UUID for Heart Rate (Movesense broadcasts this)
    private val HEART_RATE_SERVICE_UUID = UUID.fromString("0000180D-0000-1000-8000-00805f9b34fb")
    private val HEART_RATE_MEASUREMENT_CHAR_UUID = UUID.fromString("00002A37-0000-1000-8000-00805f9b34fb")

    private var bluetoothGatt: BluetoothGatt? = null

    // Connects directly via native Android BLE (Bypassing Termux limitation)
    fun connectToDevice(deviceAddress: String) {
        val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        val device: BluetoothDevice = bluetoothAdapter.getRemoteDevice(deviceAddress)
        
        Log.i(TAG, "Connecting to Movesense: $deviceAddress")
        bluetoothGatt = device.connectGatt(context, false, gattCallback)
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                Log.i(TAG, "Successfully Connected to Movesense!")
                Log.i(TAG, "Attempting to start service discovery...")
                gatt.discoverServices()
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                Log.i(TAG, "Disconnected from Movesense.")
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                val service = gatt.getService(HEART_RATE_SERVICE_UUID)
                val characteristic = service?.getCharacteristic(HEART_RATE_MEASUREMENT_CHAR_UUID)
                
                characteristic?.let {
                    Log.i(TAG, "Heart Rate Characteristic Found. Enabling Notifications (512Hz ECG stream prep)...")
                    gatt.setCharacteristicNotification(it, true)
                    
                    // Client Characteristic Configuration Descriptor
                    val descriptor = it.getDescriptor(UUID.fromString("00002902-0000-1000-8000-00805f9b34fb"))
                    descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                    gatt.writeDescriptor(descriptor)
                }
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            if (characteristic.uuid == HEART_RATE_MEASUREMENT_CHAR_UUID) {
                val flag = characteristic.properties
                val format = if ((flag and 0x01) != 0) {
                    BluetoothGattCharacteristic.FORMAT_UINT16
                } else {
                    BluetoothGattCharacteristic.FORMAT_UINT8
                }
                val heartRate = characteristic.getIntValue(format, 1)
                Log.d(TAG, "Received Heart Rate: $heartRate bpm")
                
                // TODO: Pipe raw byte[] stream to Port 4000 Hub for DSP Pan-Tompkins evaluation
            }
        }
    }
    
    fun disconnect() {
        bluetoothGatt?.close()
        bluetoothGatt = null
    }
}
