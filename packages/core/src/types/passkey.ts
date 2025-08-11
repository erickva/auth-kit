/**
 * WebAuthn/Passkey types
 */

export interface Passkey {
  id: string;
  name: string;
  credentialId: string;
  publicKey?: string;
  authenticatorType: 'platform' | 'cross-platform';
  isDiscoverable: boolean;
  lastUsedAt: string | null;
  createdAt: string;
}

export interface PasskeyRegistrationOptions {
  challenge: string;
  rp: {
    name: string;
    id: string;
  };
  user: {
    id: string;
    name: string;
    displayName: string;
  };
  pubKeyCredParams: Array<{
    type: string;
    alg: number;
  }>;
  timeout?: number;
  attestation?: 'none' | 'indirect' | 'direct' | 'enterprise';
  excludeCredentials?: Array<{
    id: string;
    type: string;
    transports?: AuthenticatorTransport[];
  }>;
  authenticatorSelection?: {
    authenticatorAttachment?: 'platform' | 'cross-platform';
    residentKey?: 'discouraged' | 'preferred' | 'required';
    userVerification?: 'discouraged' | 'preferred' | 'required';
  };
}

export interface PasskeyAuthenticationOptions {
  challenge: string;
  timeout?: number;
  rpId?: string;
  allowCredentials?: Array<{
    id: string;
    type: string;
    transports?: AuthenticatorTransport[];
  }>;
  userVerification?: 'discouraged' | 'preferred' | 'required';
}

export type AuthenticatorTransport = 
  | 'usb' 
  | 'nfc' 
  | 'ble' 
  | 'internal' 
  | 'hybrid';

export interface PasskeyCredential {
  id: string;
  type: 'public-key';
  rawId: ArrayBuffer;
  response: {
    clientDataJSON: ArrayBuffer;
    attestationObject?: ArrayBuffer;
    authenticatorData?: ArrayBuffer;
    signature?: ArrayBuffer;
    userHandle?: ArrayBuffer;
  };
  authenticatorAttachment?: 'platform' | 'cross-platform';
  clientExtensionResults?: any;
}