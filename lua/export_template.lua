-- ========== DCS Natural Language ATC Plugin ==========
-- Auto-injected by DCS-NL-ATC installer
-- This code exports aircraft state to the external ATC application

local atc_socket = nil
local atc_enabled = true
local atc_update_interval = 0.1  -- Send updates every 0.1 seconds
local atc_next_update = 0

local function atc_init()
    -- Setup LuaSocket path
    package.path = package.path..";.\\LuaSocket\\?.lua"
    package.cpath = package.cpath..";.\\LuaSocket\\?.dll"

    -- Try to load socket library
    local success, socket = pcall(require, "socket")
    if success then
        -- Create UDP socket
        atc_socket = socket.udp()
        atc_socket:settimeout(0)
        atc_socket:setsockname("*", 0)
        atc_socket:setpeername("127.0.0.1", 10308)

        log.write("DCS-NL-ATC", log.INFO, "ATC export initialized successfully")
        return true
    else
        log.write("DCS-NL-ATC", log.ERROR, "Failed to load LuaSocket: " .. tostring(socket))
        atc_enabled = false
        return false
    end
end

local function atc_export()
    if not atc_enabled or not atc_socket then
        return
    end

    -- Check if it's time to send update
    local current_time = LoGetModelTime()
    if current_time < atc_next_update then
        return
    end
    atc_next_update = current_time + atc_update_interval

    -- Gather aircraft data
    local data = {}
    data.time = current_time
    data.pilot = LoGetPilotName()

    -- Get self data (position, heading, speed, etc.)
    local selfData = LoGetSelfData()
    if selfData then
        data.position = selfData.LatLongAlt  -- {lat, lon, alt}
        data.heading = selfData.Heading
        data.pitch = selfData.Pitch
        data.bank = selfData.Bank
        data.speed = selfData.IndicatedAirSpeed  -- IAS in m/s
        data.altitude = selfData.Altitude  -- MSL in meters
        data.aoa = selfData.AngleOfAttack
        data.aoa_units = selfData.AngleOfAttackUnits
        data.vertspeed = selfData.VerticalVelocity
    end

    -- Get radio frequency
    local radio = LoGetRadioBeaconsStatus()
    if radio and radio[1] then
        data.frequency = radio[1]
    end

    -- Get aircraft type
    local type_data = LoGetSelfData()
    if type_data then
        data.aircraft_type = type_data.Name
    end

    -- Send data as simple JSON-like string
    pcall(function()
        local json_str = string.format(
            '{"type":"export","time":%.2f,"pilot":"%s","freq":%.1f,"alt":%.0f,"speed":%.1f,"heading":%.1f}' .. "\n",
            data.time or 0,
            data.pilot or "Unknown",
            data.frequency or 0,
            data.altitude or 0,
            data.speed or 0,
            data.heading or 0
        )
        atc_socket:send(json_str)
    end)
end

-- Hook into DCS export callbacks
local atc_orig_LuaExportStart = LuaExportStart
function LuaExportStart()
    atc_init()

    -- Call original LuaExportStart if it exists
    if atc_orig_LuaExportStart then
        pcall(atc_orig_LuaExportStart)
    end
end

local atc_orig_LuaExportAfterNextFrame = LuaExportAfterNextFrame
function LuaExportAfterNextFrame()
    atc_export()

    -- Call original LuaExportAfterNextFrame if it exists
    if atc_orig_LuaExportAfterNextFrame then
        pcall(atc_orig_LuaExportAfterNextFrame)
    end
end

local atc_orig_LuaExportStop = LuaExportStop
function LuaExportStop()
    -- Cleanup
    if atc_socket then
        atc_socket:close()
        atc_socket = nil
    end

    log.write("DCS-NL-ATC", log.INFO, "ATC export stopped")

    -- Call original LuaExportStop if it exists
    if atc_orig_LuaExportStop then
        pcall(atc_orig_LuaExportStop)
    end
end

log.write("DCS-NL-ATC", log.INFO, "ATC plugin hooks installed")
-- ========== End DCS Natural Language ATC Plugin ==========
