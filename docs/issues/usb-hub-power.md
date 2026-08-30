# Issue: USB power & bandwidth for sensor wiring

**Status:** Open — decision needed before final integration
**Affects:** VN-100, Ping Sonar, pressure sensor, DVL (once wired), Zed mini camera
**Owner(s):** [assign — likely an electrical/wiring team member]
**Last updated:** 2026-08-29

---

## The question this doc answers

We have several USB devices that all need to connect to the Jetson: the VN-100 (serial), Ping Sonar (serial), pressure sensor and DVL (serial, once wired), and the Zed mini camera (USB3, video). The original plan was to plug all of them into a single USB hub, which then plugs into one Jetson port. **This doc explains why that's risky as originally planned, and what to do instead.**

This is written for someone making the actual wiring/parts decision, not necessarily someone who's been following the software debugging — so it starts from first principles.

---

## Background: why this came up

While bringing up the VN-100 (see `docs/sensors/vn100.md`), we hit a real hardware-level USB failure — the Jetson's USB subsystem reported it couldn't properly configure the connection to the sensor (a timeout error, code `-110`/`ETIMEDOUT`, visible in `dmesg`). This happened with **just one sensor plugged in directly to a Jetson port** — no hub involved yet. It was resolved by trying a different physical port and cable, but it's a signal worth taking seriously: the USB setup here is already somewhat sensitive to hardware quality, even before adding the complexity of a shared hub and multiple simultaneous devices.

---

## Three separate problems a single hub can cause

It's worth understanding these as three distinct issues, because they have different symptoms and different fixes — lumping them together as "USB problems" makes it harder to diagnose if something goes wrong later.

### 1. Current budget (power)

Every device connected to a hub needs electrical current to operate. A **bus-powered** (a.k.a. passive, unpowered) hub — the cheap, common kind with no separate power brick — doesn't generate its own power. It pulls *all* the current for *every device plugged into it* through the single upstream USB port on the Jetson.

That upstream Jetson port has a current limit. If the combined draw of every attached sensor exceeds what that one port can supply, devices don't necessarily fail outright — often what happens is a **brownout**: a device gets just enough power to partially start up, or works until another device on the same hub draws a current spike, and then it drops out unpredictably. This is a notoriously hard failure mode to diagnose, because it looks like a software bug (a device "randomly disconnecting") when the actual cause is electrical.

The Zed mini camera is the biggest concern here — USB3 cameras draw meaningfully more current than simple serial sensors like the VN-100 or Ping Sonar, especially during active streaming.

**The fix:** a **powered** hub — one with its own external power adapter — supplies current to attached devices directly, rather than drawing it all through the single upstream Jetson connection. This removes the current-budget problem almost entirely, as long as the hub's own power supply is rated for the combined load of everything plugged into it.

### 2. Bandwidth contention

Separate from power: all devices on the same hub share the same upstream USB link back to the Jetson. Serial sensors (VN-100, Ping Sonar, pressure sensor, DVL) send tiny amounts of data — this is a non-issue for them individually. But the Zed mini, streaming real image data over USB3, can use a significant fraction of the total bandwidth available on that shared link, especially if streaming at higher resolution/frame rate.

Practically, this means: if the Zed shares a hub with the serial sensors, heavy camera traffic could theoretically cause the serial sensors' small, timing-sensitive data packets to be delayed or dropped, since they're competing for the same shared connection back to the Jetson.

**The fix:** give the Zed mini its own **direct** Jetson USB port, separate from any hub carrying the other sensors. This isn't just about power — it avoids the bandwidth-sharing problem entirely, since it's not sharing a link with anything else.

### 3. Single point of failure

Separate from both of the above: if every sensor is on one hub, and that hub or its one upstream connection has *any* problem — a loose cable, the hub itself failing, a firmware quirk — every sensor goes down simultaneously, mid-mission. Splitting sensors across multiple direct ports (or at least across more than one hub) means a single connection issue only takes out part of the system, not everything at once.

---

## Recommendation

1. **Zed mini camera → its own direct Jetson USB port.** Highest power draw, highest bandwidth need, and the most different from everything else — don't make it share.
2. **Remaining serial sensors (VN-100, Ping Sonar, pressure sensor, DVL) → a genuinely powered hub** (one with its own external power brick, not just "has more ports"). Check the hub's rated output current against the realistic combined draw of all four sensors' datasheets before buying — don't assume "USB hub" implies enough current for this specific combination.
3. **If the Jetson has enough physical ports available, consider skipping the hub for these too** and wiring sensors to direct ports where possible — fewer shared connections is generally safer, at the cost of needing more physical ports than a hub-based approach.
4. **Every USB-serial sensor gets a udev rule** keyed to its unique hardware serial number (already done for the VN-100 — see `docs/sensors/vn100.md` section 4). This matters *more*, not less, with multiple USB-serial devices in play: with several similar devices connected, which raw `/dev/ttyUSB*` number Linux assigns to which physical sensor becomes genuinely unpredictable and can shift between boots. Locking each one to a stable name by serial number is what keeps our launch configs and code from silently pointing at the wrong device.
5. **Physical/marine consideration, since this is a wet vehicle:** whatever hub and cabling gets chosen, make sure there's real strain relief on every connector, and minimize how far any USB cable has to run through the hull. A connection that's marginal on a dry bench can become unreliable once it's flexed, vibrated, or routed through a sealed bulkhead.

---

## What this doc is *not* saying

This is not a recommendation to build a custom PCB to solve this. A decent powered hub plus sensible port allocation solves the actual problem directly, faster and cheaper than a custom electronics board would. A consolidated PCB (integrating hub functionality alongside power distribution, fusing, etc.) could make sense as a *future* project once the software stack is more mature, but it's not the right response to this specific issue right now.

---

## Open items for whoever picks this up

- [ ] Confirm exact current draw for each sensor (check datasheets) and size the powered hub's power supply accordingly
- [ ] Confirm the Jetson has a free, adequate port for the Zed mini's direct connection
- [ ] Decide: powered hub for the remaining sensors, or direct ports for all of them if enough are physically available
- [ ] Once wiring is finalized, update this doc's status and note the actual hub/port assignments chosen, for whoever wires the next revision of the vehicle

---

## References

- Related club docs: `docs/sensors/vn100.md` (the USB timeout error that prompted this), `docs/architecture-roadmap.md`
