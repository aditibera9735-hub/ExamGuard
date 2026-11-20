
(function () {
    "use strict";

    const config = window.EXAMGUARD_CONFIG || {};

    const candidateId = config.candidateId;
    const sessionId = config.sessionId;

    const API_URL = "/api/browser-events";

    const activeEvents = new Map();
    let currentIncidentId = null;

    function getTimestamp() {
        return new Date().toISOString();
    }

    function startEvent(eventType) {
        if (activeEvents.has(eventType)) {
            return;
        }

        // Use the same incident ID for overlapping browser events.
        if (activeEvents.size === 0) {
            currentIncidentId =
                "browser-" + Date.now() + "-" +
                Math.random().toString(36).slice(2, 8);
        }

        activeEvents.set(eventType, {
            startTime: getTimestamp(),
            incidentId: currentIncidentId
        });
    }

    async function sendEvent(eventType, startTime, endTime, incidentId) {
        if (!candidateId || !sessionId) {
            console.warn("ExamGuard: Session information missing.");
            return;
        }

        const duration = Math.max(
            0,
            (new Date(endTime) - new Date(startTime)) / 1000
        );

        const eventData = {
            candidate_id: candidateId,
            session_id: sessionId,
            event_type: eventType,
            source: "browser",
            timestamp: startTime,
            severity: "MEDIUM",
            metadata: {
                start_time: startTime,
                end_time: endTime,
                duration_seconds: duration,
                incident_id: incidentId
            }
        };

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(eventData)
            });

            if (!response.ok) {
                console.error(
                    "ExamGuard event failed:",
                    response.status
                );
                return;
            }

            console.log("ExamGuard event recorded:", eventType);

        } catch (error) {
            console.error("Browser event delivery failed:", error);
        }
    }

    function endEvent(eventType) {
        if (!activeEvents.has(eventType)) {
            return;
        }

        const eventInfo = activeEvents.get(eventType);
        const endTime = getTimestamp();

        activeEvents.delete(eventType);

        sendEvent(
            eventType,
            eventInfo.startTime,
            endTime,
            eventInfo.incidentId
        );

        if (activeEvents.size === 0) {
            currentIncidentId = null;
        }
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            startEvent("TAB_HIDDEN");
        } else {
            endEvent("TAB_HIDDEN");
        }
    });

    window.addEventListener("blur", function () {
        startEvent("FOCUS_LOST");
    });

    window.addEventListener("focus", function () {
        endEvent("FOCUS_LOST");
    });

    document.addEventListener("fullscreenchange", function () {
        if (!document.fullscreenElement) {
            const now = getTimestamp();

            sendEvent(
                "FULLSCREEN_EXIT",
                now,
                now,
                "fullscreen-" + Date.now()
            );
        }
    });

    console.log("ExamGuard browser monitoring initialized.");

})();
