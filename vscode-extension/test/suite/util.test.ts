/**
 * Unit tests for utility functions
 */

import * as assert from 'assert';
import { getNonce } from '../../src/util';

suite('Util Test Suite', () => {
    suite('getNonce', () => {
        test('should generate a 32-character string', () => {
            const nonce = getNonce();
            assert.strictEqual(nonce.length, 32);
        });

        test('should generate alphanumeric characters only', () => {
            const nonce = getNonce();
            assert.match(nonce, /^[A-Za-z0-9]+$/);
        });

        test('should generate different nonces on each call', () => {
            const nonce1 = getNonce();
            const nonce2 = getNonce();
            const nonce3 = getNonce();

            assert.notStrictEqual(nonce1, nonce2);
            assert.notStrictEqual(nonce2, nonce3);
            assert.notStrictEqual(nonce1, nonce3);
        });

        test('should always return strings of the same length', () => {
            for (let i = 0; i < 100; i++) {
                const nonce = getNonce();
                assert.strictEqual(nonce.length, 32);
            }
        });
    });
});
