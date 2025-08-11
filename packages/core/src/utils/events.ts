/**
 * Event system for authentication events
 */

import { AuthEvent, AuthEventType } from '../types';

export type EventListener = (event: AuthEvent) => void;

export class AuthEventEmitter {
  private listeners: Map<AuthEventType, Set<EventListener>>;
  private globalListeners: Set<EventListener>;

  constructor() {
    this.listeners = new Map();
    this.globalListeners = new Set();
  }

  /**
   * Subscribe to a specific event type
   */
  on(type: AuthEventType, listener: EventListener): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    
    this.listeners.get(type)!.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.get(type)?.delete(listener);
    };
  }

  /**
   * Subscribe to all events
   */
  onAny(listener: EventListener): () => void {
    this.globalListeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.globalListeners.delete(listener);
    };
  }

  /**
   * Subscribe to an event only once
   */
  once(type: AuthEventType, listener: EventListener): () => void {
    const wrappedListener = (event: AuthEvent) => {
      listener(event);
      this.off(type, wrappedListener);
    };

    return this.on(type, wrappedListener);
  }

  /**
   * Unsubscribe from a specific event type
   */
  off(type: AuthEventType, listener: EventListener): void {
    this.listeners.get(type)?.delete(listener);
  }

  /**
   * Emit an event
   */
  emit(type: AuthEventType, data?: any): void {
    const event: AuthEvent = {
      type,
      timestamp: new Date(),
      data
    };

    // Emit to specific listeners
    this.listeners.get(type)?.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error(`Error in auth event listener for ${type}:`, error);
      }
    });

    // Emit to global listeners
    this.globalListeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error(`Error in global auth event listener:`, error);
      }
    });

    // Also emit as browser custom event for cross-component communication
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(`auth:${type}`, { detail: data }));
    }
  }

  /**
   * Clear all listeners
   */
  clear(): void {
    this.listeners.clear();
    this.globalListeners.clear();
  }

  /**
   * Get the number of listeners for a specific event
   */
  listenerCount(type?: AuthEventType): number {
    if (type) {
      return (this.listeners.get(type)?.size || 0) + this.globalListeners.size;
    }
    
    let total = this.globalListeners.size;
    this.listeners.forEach(listeners => {
      total += listeners.size;
    });
    return total;
  }
}

// Create a singleton instance
export const authEvents = new AuthEventEmitter();

// Helper function to listen to browser custom events
export function listenToAuthEvent(
  type: AuthEventType,
  callback: (data: any) => void
): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const handler = (event: Event) => {
    const customEvent = event as CustomEvent;
    callback(customEvent.detail);
  };

  window.addEventListener(`auth:${type}`, handler);

  return () => {
    window.removeEventListener(`auth:${type}`, handler);
  };
}