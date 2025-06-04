# Hybrid-MPlane Test Procedure: NETCONF Call Home Establishment

## Test Case ID
TC-HMP-001

## Title
Verify that the O-RU initiates a NETCONF Call Home session to the O-RU Controller over the M-Plane interface.

## Objective
To confirm that, in a Hybrid-MPlane deployment, the O-RU is able to discover the O-RU Controller via DHCP and successfully initiate a NETCONF Call Home session after power-on.

## Scope
This test verifies the expected behavior from the O-RU Controller’s point of view. It is applicable in setups where the O-RU Controller (typically part of the SMO) acts as the NETCONF server endpoint.

---

## Preconditions
- The O-RU Controller is running and ready to accept NETCONF Call Home sessions.
- A DHCP server is configured to provide the O-RU Controller’s FQDN or IP address (e.g., via Option 43 for IPv4).
- No NETCONF session is currently active between the O-RU and the Controller.
- Monitoring tools or logs are available to verify session establishment on the Controller side.

---

## Test Steps

1. **Ensure Clean State**
   - Confirm that no NETCONF session is active for the O-RU under test.

2. **Power On O-RU**
   - Start or reboot the O-RU so that it performs DHCP-based discovery and attempts to initiate a NETCONF session.

3. **Observe DHCP Behavior**
   - Confirm that the O-RU receives its network configuration, including the address of the O-RU Controller.

4. **Wait for Connection Attempt**
   - Monitor the O-RU Controller (passively) for incoming NETCONF Call Home sessions.

5. **Verify Session Establishment**
   - Confirm that a new NETCONF session from the O-RU appears.
   - The session must be marked as successfully connected/stable.

6. **Inspect Session Metadata**
   - Optionally, check the reported capabilities or session parameters (e.g., IP address, authentication method, YANG modules).

---

## Expected Result
- The O-RU initiates a NETCONF Call Home session after power-on.
- The O-RU Controller receives and accepts the session.
- The session is established and marked as active.

---

## Pass Criteria
- One new NETCONF session appears on the O-RU Controller.
- Session is marked as active/connected.
- No protocol or authentication errors occur during session establishment.

## Fail Criteria
- No NETCONF session is observed within a reasonable timeout (e.g., 60 seconds).
- Connection attempt fails due to transport errors, authentication, or configuration issues.
- The session is established but drops or fails during handshake.

---

## Postconditions
- The session remains active, and the O-RU is ready for further M-Plane interaction (e.g., capability exchange, supervision).

---

## Test Observables and Artifacts

| Artifact | Description |
|----------|-------------|
| **Session Log** | Log entry showing new NETCONF connection from the O-RU |
| **Timestamp** | Time when the session was established |
| **Session Metadata** | IP address, username, authentication method, transport (SSH/TLS) |
| **YANG Capabilities** | Modules advertised in `<hello>` message (optional) |
| **Log Files** | Raw logs or exported traces from the O-RU Controller and DHCP server (optional) |

---

## Session Metadata Expectations

Upon session establishment, the O-RU is expected to:
- Advertise its supported YANG modules via `<hello>`
- Present a known username (e.g., `smo`)
- Authenticate using SSH public key or certificate (if TLS is used)
- Use the expected IP version and transport

---

## Configuration Assumptions

| Component | Assumption |
|-----------|------------|
| **DHCP Server** | Provides O-RU Controller FQDN or IP via Option 43 (IPv4) or equivalent |
| **O-RU Credentials** | Pre-provisioned on the Controller (e.g., public key for SSH) |
| **O-RU Controller Address** | Reachable from O-RU’s management VLAN |
| **NETCONF Listening Port** | Known and open (e.g., TCP port 830 for SSH) |

---
