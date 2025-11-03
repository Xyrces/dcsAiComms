-- DCS Natural Language ATC Mission Script
-- This script runs in the mission environment to provide ATC services
-- Load this via mission triggers or DO SCRIPT FILE

ATCSystem = {}
ATCSystem.version = "1.0.0"
ATCSystem.players = {}
ATCSystem.airbases = {}
ATCSystem.states = {
    STARTUP = "STARTUP",
    TAXI = "TAXI",
    READY = "READY",
    TAKEOFF = "TAKEOFF",
    AIRBORNE = "AIRBORNE",
    APPROACH = "APPROACH",
    LANDING = "LANDING",
    LANDED = "LANDED"
}

-- Initialize ATC System
function ATCSystem:init()
    env.info("DCS-NL-ATC: Initializing ATC System v" .. self.version)

    -- Discover all airbases
    for _, side in pairs({coalition.side.BLUE, coalition.side.RED, coalition.side.NEUTRAL}) do
        local bases = coalition.getAirbases(side)
        if bases then
            for _, airbase in pairs(bases) do
                local name = airbase:getName()
                local pos = airbase:getPosition().p

                self.airbases[name] = {
                    airbase = airbase,
                    coalition = side,
                    position = pos,
                    tower_freq = 251.0,  -- Default tower frequency
                    ground_freq = 249.5,  -- Default ground frequency
                    active_runway = nil
                }

                env.info("DCS-NL-ATC: Found airbase - " .. name)
            end
        end
    end

    -- Register event handler
    world.addEventHandler(self.eventHandler)

    -- Display initialization message
    trigger.action.outText("Natural Language ATC System Initialized", 10, false)
    env.info("DCS-NL-ATC: System initialized successfully")
end

-- Event handler
ATCSystem.eventHandler = {}
function ATCSystem.eventHandler:onEvent(event)
    if event == nil or event.initiator == nil then
        return
    end

    local unit = event.initiator

    -- Player enters unit
    if event.id == world.event.S_EVENT_PLAYER_ENTER_UNIT then
        ATCSystem:onPlayerEnter(unit)

    -- Player birth (alternative detection)
    elseif event.id == world.event.S_EVENT_BIRTH then
        if unit:getPlayerName() then
            ATCSystem:onPlayerEnter(unit)
        end

    -- Takeoff event
    elseif event.id == world.event.S_EVENT_TAKEOFF then
        ATCSystem:onTakeoff(unit)

    -- Landing event
    elseif event.id == world.event.S_EVENT_LAND then
        ATCSystem:onLanding(unit)

    -- Engine startup
    elseif event.id == world.event.S_EVENT_ENGINE_STARTUP then
        ATCSystem:onEngineStartup(unit)

    -- Engine shutdown
    elseif event.id == world.event.S_EVENT_ENGINE_SHUTDOWN then
        ATCSystem:onEngineShutdown(unit)
    end
end

-- Player enters unit
function ATCSystem:onPlayerEnter(unit)
    if not unit or not unit:isExist() then
        return
    end

    local playerName = unit:getPlayerName()
    if not playerName then
        return
    end

    local unitName = unit:getName()
    local group = unit:getGroup()

    if not group then
        return
    end

    local groupID = group:getID()
    local typeName = unit:getTypeName()

    self.players[unitName] = {
        unit = unit,
        playerName = playerName,
        groupID = groupID,
        typeName = typeName,
        callsign = unit:getCallsign(),
        state = self.states.STARTUP,
        airbase = nil,
        cleared_runway = nil,
        last_update = timer.getTime()
    }

    env.info(string.format("DCS-NL-ATC: Player %s entered %s (%s)", playerName, typeName, unitName))

    -- Notify player
    trigger.action.outTextForUnit(
        unit:getID(),
        "Natural Language ATC Active\nUse your radio for ATC communications",
        15,
        false
    )
end

-- Handle takeoff event
function ATCSystem:onTakeoff(unit)
    local unitName = unit:getName()
    local player = self.players[unitName]

    if player then
        player.state = self.states.AIRBORNE
        player.last_update = timer.getTime()
        env.info("DCS-NL-ATC: Player " .. player.playerName .. " has taken off")
    end
end

-- Handle landing event
function ATCSystem:onLanding(unit)
    local unitName = unit:getName()
    local player = self.players[unitName]

    if player then
        player.state = self.states.LANDED
        player.last_update = timer.getTime()
        env.info("DCS-NL-ATC: Player " .. player.playerName .. " has landed")
    end
end

-- Handle engine startup
function ATCSystem:onEngineStartup(unit)
    local unitName = unit:getName()
    local player = self.players[unitName]

    if player and player.state == self.states.STARTUP then
        env.info("DCS-NL-ATC: Player " .. player.playerName .. " started engines")
    end
end

-- Handle engine shutdown
function ATCSystem:onEngineShutdown(unit)
    local unitName = unit:getName()
    local player = self.players[unitName]

    if player then
        player.state = self.states.SHUTDOWN
        env.info("DCS-NL-ATC: Player " .. player.playerName .. " shut down engines")
    end
end

-- Get nearest airbase to unit
function ATCSystem:getNearestAirbase(unit)
    if not unit or not unit:isExist() then
        return nil
    end

    local unitPos = unit:getPosition().p
    local nearestBase = nil
    local nearestDist = math.huge

    for name, baseInfo in pairs(self.airbases) do
        local basePos = baseInfo.position
        local dist = ((unitPos.x - basePos.x)^2 + (unitPos.z - basePos.z)^2)^0.5

        if dist < nearestDist then
            nearestDist = dist
            nearestBase = name
        end
    end

    return nearestBase, nearestDist
end

-- Update player state (call periodically)
function ATCSystem:update()
    local currentTime = timer.getTime()

    for unitName, player in pairs(self.players) do
        -- Check if unit still exists
        if not player.unit:isExist() then
            self.players[unitName] = nil
        else
            -- Update airbase proximity
            local nearestBase, dist = self:getNearestAirbase(player.unit)
            if nearestBase then
                player.airbase = nearestBase
                player.airbase_distance = dist
            end
        end
    end
end

-- Start periodic update timer
timer.scheduleFunction(
    function()
        ATCSystem:update()
        return timer.getTime() + 1.0  -- Update every second
    end,
    nil,
    timer.getTime() + 1.0
)

-- Initialize on script load
ATCSystem:init()

env.info("DCS-NL-ATC: Mission script loaded successfully")
