#!/usr/bin/env swift
import Foundation
import Contacts
import Dispatch

func containerTypeName(_ type: CNContainerType) -> String {
    switch type {
    case .unassigned: return "unassigned"
    case .local: return "local"
    case .exchange: return "exchange"
    case .cardDAV: return "carddav"
    @unknown default: return "unknown"
    }
}

func authorizationStatusName(_ status: CNAuthorizationStatus) -> String {
    switch status {
    case .notDetermined: return "not_determined"
    case .restricted: return "restricted"
    case .denied: return "denied"
    case .authorized: return "authorized"
    case .limited: return "limited"
    @unknown default: return "unknown"
    }
}

func fullAccessError(_ status: CNAuthorizationStatus) -> NSError {
    let statusName = authorizationStatusName(status)
    let message: String
    switch status {
    case .limited:
        message = "Contacts access is Limited. LLM4LIFE sync verification requires Full Access so it can enumerate the complete Google-synced contact container. Open System Settings > Privacy & Security > Contacts, select the terminal app used to run this command, and grant Full Access; then rerun."
    case .denied:
        message = "Contacts access is denied. Open System Settings > Privacy & Security > Contacts, enable access for the terminal app used to run this command, choose Full Access if macOS offers an access level, and rerun."
    case .restricted:
        message = "Contacts access is restricted by macOS policy and cannot be changed by this script. Review System Settings > Privacy & Security > Contacts and any device-management or parental restrictions."
    default:
        message = "Full Contacts access is required for sync verification. Open System Settings > Privacy & Security > Contacts and grant Full Access to the terminal app used to run this command; then rerun."
    }
    return NSError(
        domain: "LLM4LIFE.AppleContactsExport",
        code: 77,
        userInfo: [
            NSLocalizedDescriptionKey: message,
            "authorization_status": statusName,
        ]
    )
}

func ensureContactsFullAccess(_ store: CNContactStore) throws {
    var status = CNContactStore.authorizationStatus(for: .contacts)
    if status == .authorized {
        return
    }

    if status == .notDetermined {
        let semaphore = DispatchSemaphore(value: 0)
        var requestError: Error?
        store.requestAccess(for: .contacts) { _, error in
            requestError = error
            semaphore.signal()
        }
        semaphore.wait()

        if let requestError = requestError {
            throw requestError
        }

        // A successful request can now result in Limited Access. Re-read the
        // authorization state and require true Full Access before enumerating
        // containers for whole-address-book reconciliation.
        status = CNContactStore.authorizationStatus(for: .contacts)
        if status == .authorized {
            return
        }
    }

    throw fullAccessError(status)
}

func jsonError(_ error: Error) -> String {
    let nsError = error as NSError
    var payload: [String: Any] = [
        "error": "apple_contacts_export_failed",
        "domain": nsError.domain,
        "code": nsError.code,
        "message": nsError.localizedDescription,
    ]
    if let status = nsError.userInfo["authorization_status"] as? String {
        payload["authorization_status"] = status
    }
    if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]),
       let text = String(data: data, encoding: .utf8) {
        return text
    }
    return "{\"error\":\"apple_contacts_export_failed\"}"
}

func run() throws {
    let args = CommandLine.arguments
    if args.count != 2 {
        fputs("Usage: swift scripts/apple_contacts_live_export.swift <private-output.json>\n", stderr)
        exit(64)
    }

    let outputURL = URL(fileURLWithPath: args[1])
    let store = CNContactStore()

    try ensureContactsFullAccess(store)

    let keys: [CNKeyDescriptor] = [
        CNContactIdentifierKey as CNKeyDescriptor,
        CNContactFormatter.descriptorForRequiredKeys(for: .fullName),
        CNContactEmailAddressesKey as CNKeyDescriptor,
        CNContactPhoneNumbersKey as CNKeyDescriptor,
        CNContactPostalAddressesKey as CNKeyDescriptor,
        CNContactBirthdayKey as CNKeyDescriptor,
        CNContactOrganizationNameKey as CNKeyDescriptor,
        CNContactDepartmentNameKey as CNKeyDescriptor,
        CNContactJobTitleKey as CNKeyDescriptor,
        CNContactUrlAddressesKey as CNKeyDescriptor,
        CNContactImageDataAvailableKey as CNKeyDescriptor,
    ]

    var exportedContainers: [[String: Any]] = []
    for container in try store.containers(matching: nil) {
        let predicate = CNContact.predicateForContactsInContainer(withIdentifier: container.identifier)
        let contacts = try store.unifiedContacts(matching: predicate, keysToFetch: keys)
        var exportedContacts: [[String: Any]] = []
        exportedContacts.reserveCapacity(contacts.count)

        for contact in contacts {
            let displayName = CNContactFormatter.string(from: contact, style: .fullName) ?? ""
            let emails = contact.emailAddresses.map { String($0.value) }
            let phones = contact.phoneNumbers.map { $0.value.stringValue }
            let hasOrganization = !contact.organizationName.isEmpty || !contact.departmentName.isEmpty || !contact.jobTitle.isEmpty

            exportedContacts.append([
                "display_name": displayName,
                "emails": emails,
                "phones": phones,
                "field_presence": [
                    "address": !contact.postalAddresses.isEmpty,
                    "birthday": contact.birthday != nil,
                    "organization": hasOrganization,
                    "urls": !contact.urlAddresses.isEmpty,
                    "photos": contact.imageDataAvailable,
                ],
            ])
        }

        exportedContainers.append([
            "type": containerTypeName(container.type),
            "contacts": exportedContacts,
        ])
    }

    let formatter = ISO8601DateFormatter()
    let payload: [String: Any] = [
        "schema_version": 1,
        "generated_at": formatter.string(from: Date()),
        "containers": exportedContainers,
        "privacy": [
            "private_runtime_snapshot": true,
            "provider_container_ids_omitted": true,
            "container_names_omitted": true,
            "notes_omitted": true,
        ],
    ]

    let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
    try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    try data.write(to: outputURL, options: .atomic)
    print("{\"private_output\":\"\(args[1])\",\"containers\":\(exportedContainers.count)}")
}

do {
    try run()
} catch {
    fputs(jsonError(error) + "\n", stderr)
    exit(77)
}
