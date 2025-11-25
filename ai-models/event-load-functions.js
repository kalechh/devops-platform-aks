'use strict';

/* ---------------------------------------------------------------------
   GLOBALS
   ------------------------------------------------------------------ */

/**
 * One timestamp shared by every virtual user (vuser).
 * Because it’s defined at module scope, it is evaluated once per Node
 * process and every vuser inside that process reads the same value.
 */
const globalTestStartTime = Date.now();

/** Helper: whole minutes that have elapsed since a given epoch (ms). */
const minutesSince = (epochMs) =>
  Math.floor((Date.now() - epochMs) / 60_000);

/* ---------------------------------------------------------------------
   EXPORTS
   ------------------------------------------------------------------ */

module.exports = {
  /* ───────────────────────────────
     DATA-GENERATION HELPERS
     ──────────────────────────────*/

  // Generate realistic event data with phase-aware variations
  generateEventData(context, events, done) {
    const eventTypes = [
      'Tech Conference 2025',            'Annual Music Festival',
      'Art Gallery Opening',             'Business Leadership Summit',
      'International Sports Tournament', 'Culinary Food Festival',
      'Cultural Heritage Event',         'Professional Workshop',
      'Industry Networking Mixer',       'Product Launch Showcase',
      'Skills Training Bootcamp',        'Charity Fundraising Gala',
      'Innovation Symposium',            'Startup Pitch Competition',
      'Academic Research Conference',    'Community Celebration'
    ];
    const venues = [
      'Grand Convention Center', 'Metropolitan City Hall',
      'Olympic Stadium Complex', 'Luxury Hotel Ballroom',
      'University Main Campus',  'Downtown Community Center',
      'Riverside Park Pavilion', 'Historic Theater District',
      'Modern Art Museum',       'Corporate Conference Center',
      'International Exhibition Hall', 'Scenic Outdoor Amphitheater',
      'Innovation Hub Facility', 'Cultural Arts Complex',
      'Sports Arena',            'Waterfront Event Space'
    ];
    const cities = [
      'New York, NY',  'Los Angeles, CA', 'Chicago, IL',    'Houston, TX',
      'Phoenix, AZ',   'Philadelphia, PA','San Antonio, TX','San Diego, CA',
      'Dallas, TX',    'Austin, TX',      'Jacksonville, FL','Fort Worth, TX',
      'Columbus, OH',  'Indianapolis, IN','Charlotte, NC',  'San Francisco, CA'
    ];

    const elapsed = minutesSince(globalTestStartTime);

    // PHASE LOGIC: (30/20/25/30/15)
    let phasePrefix = '';
    let ticketMultiplier = 1;
    if (elapsed < 30) {
      phasePrefix = '[Medium-1]';  ticketMultiplier = 1.2;
    } else if (elapsed < 50) {
      phasePrefix = '[Light-1]';   ticketMultiplier = 0.8;
    } else if (elapsed < 75) {
      phasePrefix = '[Heavy]';     ticketMultiplier = 2.0;
    } else if (elapsed < 105) {
      phasePrefix = '[Medium-2]';  ticketMultiplier = 1.2;
    } else {
      phasePrefix = '[Light-2]';   ticketMultiplier = 0.8;
    }

    const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const venue     = venues[Math.floor(Math.random() * venues.length)];
    const city      = cities[Math.floor(Math.random() * cities.length)];

    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + Math.floor(Math.random() * 90) + 7);

    const baseTickets  = /Stadium|Festival/.test(eventType) ? 1000 : 200;
    const ticketCount  = Math.floor((baseTickets + Math.random() * 500) * ticketMultiplier);

    context.vars.eventDescription = `${phasePrefix} ${eventType} - LoadTest Event ${Math.floor(Math.random() * 100000)}`;
    context.vars.eventDate        = futureDate.toISOString().split('T')[0];
    context.vars.ticketNumber     = ticketCount;
    context.vars.additionalNotes  = `Phase: ${phasePrefix} | Generated: ${new Date().toISOString()} | Contact: loadtest-${Math.floor(Math.random() * 1000)}@example.com | Capacity: ${ticketCount}`;
    context.vars.eventPlace       = `${venue}, ${city}`;
    return done();
  },

  // Generate update data with realistic modifications
  generateUpdateData(context, events, done) {
    const reasons = [
      'Venue upgraded due to overwhelming demand', 'Additional premium tickets now available',
      'Celebrity guest speaker confirmed',         'Schedule extended with bonus sessions',
      'Major sponsorship partnership announced',   'VIP package options added',
      'Early bird pricing extended',               'Accessibility improvements completed',
      'Live streaming option added',               'Catering menu enhanced'
    ];
    const reason          = reasons[Math.floor(Math.random() * reasons.length)];
    const ticketIncrease  = Math.floor(Math.random() * 150) + 25;

    context.vars.updatedDescription = `${context.vars.eventDescription} - UPDATED: ${reason}`;
    context.vars.updatedTickets     = context.vars.ticketNumber + ticketIncrease;
    context.vars.updatedNotes       = `UPDATED: ${reason} | Previous capacity: ${context.vars.ticketNumber} | New capacity: ${context.vars.updatedTickets} | Updated: ${new Date().toISOString()}`;
    return done();
  },

  // Generate bulk event data for database stress testing
  generateBulkEventData(context, events, done) {
    const bulkTypes   = [ 'Workshop Series','Training Bootcamp','Certification Program','Masterclass Collection','Conference Track','Seminar Series' ];
    const identifiers = [ 'Alpha','Beta','Gamma','Delta','Epsilon','Zeta' ];
    const bulkType    = bulkTypes[Math.floor(Math.random() * bulkTypes.length)];
    const batchId     = identifiers[Math.floor(Math.random() * identifiers.length)];

    const bulkDate = new Date();
    bulkDate.setDate(bulkDate.getDate() + Math.floor(Math.random() * 30) + 15);

    context.vars.bulkEventDescription = `Bulk ${bulkType} - Batch ${batchId} Series ${Math.floor(Math.random() * 10000)}`;
    context.vars.bulkEventDate        = bulkDate.toISOString().split('T')[0];
    context.vars.bulkTicketNumber     = Math.floor(Math.random() * 300) + 100;
    context.vars.bulkEventPlace       = `Load Test Facility ${Math.floor(Math.random() * 100)}, Training Center Complex`;
    return done();
  },

  /* ───────────────────────────────
     STRESS-TEST FUNCTIONS
     ──────────────────────────────*/

  // CPU-intensive operations to trigger HPA scaling
  cpuStressTest(context, events, done) {
    const startTime   = Date.now();
    const iterations  = Math.floor(Math.random() * 75_000) + 25_000; // 25k-100k
    let   result      = 0;

    for (let i = 0; i < iterations; i++) {
      result += Math.sqrt(i) * Math.sin(i / 100) * Math.cos(i / 50);
      if (i % 1000 === 0) {
        for (let j = 2; j < 100; j++) {
          let prime = true;
          for (let k = 2; k <= Math.sqrt(j); k++) {
            if (j % k === 0) { prime = false; break; }
          }
          if (prime) result += j;
        }
      }
    }

    // Memory allocation stress
    const largeArray = Array.from({ length: Math.floor(Math.random() * 10_000) + 5_000 }, (_, i) => ({
      id: i,
      data: Math.random().toString(36).slice(2, 15),
      timestamp: Date.now(),
      computed: Math.sqrt(i) * Math.PI
    }));

    const executionTime = Date.now() - startTime;
    context.vars.cpuResult        = result;
    context.vars.cpuExecutionTime = executionTime;
    context.vars.cpuIterations    = iterations;
    context.vars.memoryAllocated  = largeArray.length;

    if (Math.random() < 0.10) {
      console.log(`[CPU-STRESS] ${iterations} iterations in ${executionTime} ms, allocated ${largeArray.length} objects`);
    }
    return done();
  },

  // Memory stress test for database and application servers
  memoryStressTest(context, events, done) {
    const startTime   = Date.now();
    const objectCount = Math.floor(Math.random() * 5_000) + 2_000; // 2k-7k
    const memoryData  = [];

    for (let i = 0; i < objectCount; i++) {
      memoryData.push({
        id: `stress_${i}_${Date.now()}`,
        eventData: {
          title: `Memory Stress Event ${i}`,
          description: 'A'.repeat(Math.floor(Math.random() * 500) + 100),
          attendees: Array.from({ length: Math.floor(Math.random() * 50) + 10 }, (_, idx) => ({
            id: idx,
            name: `Attendee_${idx}_${Math.random().toString(36).slice(2, 8)}`,
            email: `test${idx}@example.com`,
            registered: new Date().toISOString()
          })),
          metadata: {
            created: new Date().toISOString(),
            tags: ['load-test','memory-stress',`phase-${Math.floor(Math.random() * 5) + 1}`],
            settings: {
              notifications: true,
              reminders: Math.floor(Math.random() * 5),
              priority:   Math.floor(Math.random() * 10)
            }
          }
        },
        computedValues: Array.from({ length: 100 }, (_, idx) => Math.random() * idx),
        timestamp: Date.now()
      });
    }

    const totalSize   = memoryData.reduce((s, item) => s + JSON.stringify(item).length, 0);
    const avgAttend   = memoryData.reduce((s, item) => s + item.eventData.attendees.length, 0) / memoryData.length;
    const execTime    = Date.now() - startTime;

    context.vars.memoryObjectsCreated = objectCount;
    context.vars.memoryTotalSize      = totalSize;
    context.vars.memoryAvgAttendees   = Math.floor(avgAttend);
    context.vars.memoryExecutionTime  = execTime;

    memoryData.length = 0; // free memory
    return done();
  },

  /* ───────────────────────────────
     FLOW UTILITIES
     ──────────────────────────────*/

  // Enhanced phase logging (now uses the shared global timestamp)
  logPhaseInfo(context, events, done) {
    const elapsed = minutesSince(globalTestStartTime);

    let phase        = 'Unknown';
    let expectedLoad = 'N/A';
    let expectedPods = 'N/A';

    if (elapsed < 30) {
      phase        = 'Phase 1: Medium Load';
      expectedLoad = '45-55 RPS';
      expectedPods = '3-5 pods, 2-3 nodes';
    } else if (elapsed < 50) {
      phase        = 'Phase 2: Light Load';
      expectedLoad = '10 RPS';
      expectedPods = '1-2 pods, 1-2 nodes';
    } else if (elapsed < 75) {
      phase        = 'Phase 3: Heavy Load';
      expectedLoad = '90-110 RPS';
      expectedPods = '8-12 pods, 4-6 nodes';
    } else if (elapsed < 105) {
      phase        = 'Phase 4: Medium Load';
      expectedLoad = '45-55 RPS';
      expectedPods = '3-5 pods, 2-3 nodes';
    } else {
      phase        = 'Phase 5: Light Load';
      expectedLoad = '10 RPS';
      expectedPods = '1-2 pods, 1-2 nodes';
    }

    if (Math.random() < 0.05) {
      console.log(`[${new Date().toISOString()}] ${phase} | Elapsed ${elapsed} min | Expected ${expectedLoad} → ${expectedPods}`);
    }

    context.vars.currentPhase   = phase;
    context.vars.elapsedMinutes = elapsed;
    context.vars.expectedLoad   = expectedLoad;
    return done();
  },

  // Dynamic think-time based on phase
  dynamicThinkTime(context, events, done) {
    const elapsed = context.vars.elapsedMinutes || minutesSince(globalTestStartTime);
    let base  = 2000; // ms
    let range = 3000;

    if (elapsed < 30 || (elapsed >= 75 && elapsed < 105)) {      // medium
      base = 2500; range = 4000;
    } else if (elapsed < 50 || elapsed >= 105) {                 // light
      base = 4000; range = 6000;
    } else {                                                     // heavy
      base = 1000; range = 2000;
    }

    context.vars.dynamicThinkTime = Math.floor(base + Math.random() * range);
    return done();
  },

  // Enhanced error handler
  handleError(context, events, done) {
    const err      = context.vars.$error;
    const phase    = context.vars.currentPhase || 'Unknown Phase';
    const elapsed  = context.vars.elapsedMinutes || minutesSince(globalTestStartTime);

    if (err) {
      console.error(`[ERROR] ${new Date().toISOString()} | ${phase} (${elapsed} min) | ${err.message || 'Unknown error'}`);
      context.vars.errorPhase = phase;
      context.vars.errorTime  = elapsed;
    }
    return done();
  },

  // Initialize test start-time (per vuser) but copy the GLOBAL stamp
  initializeTest(context, events, done) {
    context.vars.$testStartTime = globalTestStartTime;
    if (!global.__initBannerPrinted) {
      console.log(`[INIT] Load test started at ${new Date(globalTestStartTime).toISOString()}`);
      global.__initBannerPrinted = true;
    }
    return done();
  },

  // Generate realistic search queries
  generateSearchQuery(context, events, done) {
    const terms  = [ 'conference','workshop','festival','seminar','training','networking','exhibition','summit','bootcamp','masterclass' ];
    const places = [ 'New York','California','Texas','Florida','Chicago','Boston','Seattle','Denver','Atlanta','Phoenix' ];
    const months = [ 'January','February','March','April','May','June','July','August','September','October','November','December' ];

    const rnd = Math.random();
    let query = rnd < 0.4 ? terms[Math.floor(Math.random() * terms.length)]
             : rnd < 0.7 ? places[Math.floor(Math.random() * places.length)]
             :             months[Math.floor(Math.random() * months.length)];

    context.vars.searchQuery = query;
    context.vars.searchPage  = Math.floor(Math.random() * 5);
    context.vars.searchSize  = [10, 20, 50][Math.floor(Math.random() * 3)];
    return done();
  }
};
