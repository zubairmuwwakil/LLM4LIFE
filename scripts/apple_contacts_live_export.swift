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

func ensureContactsAccess(_ store: CNContactStore) throws {
    let status = CNContactStore.authorizationStatus(for: .contacts)
    if status == .authorized {
        return
    }
    if status == .notDetermined {
        let semaphore = DispatchSemaphore(value: 0)
        var granted = false
        var requestError: Error?
        store.requestAccess(for: .contacts) { ok, error in
            granted = ok
            requestError = error
            semaphore.signal()
        }
        semaphore.wait()
        if granted {
            return
        }
        if let requestError = requestError {
            throw requestError
        }
    }
    throw NSError(
        domain: "LLM4LIFE.AppleContactsExport",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Full Contacts read access is required for sync verification."]
    )
}

let args = CommandLine.arguments
if args.count != 2 {
    fputs("Usage: swift scripts/apple_contacts_live_export.swift <private-output.json>\n", stderr)
    exit(64)
}

let outputURL = URL(fileURLWithPath: args[1])
let store = CNContactStore()

try ensureContactsAccess(store)

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
