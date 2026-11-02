import unittest
from agent_tool_adapters import AdapterError, AdapterRegistry, Invocation, PolicyDecision

class Echo:
    adapter_id = "test.echo"
    capabilities = frozenset({"test.echo"})
    def invoke(self, input_data):
        return {"received": input_data}

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AdapterRegistry()
        self.registry.register(Echo())
        self.allow = lambda _: PolicyDecision(True, "test-allow")
        self.deny = lambda _: PolicyDecision(False, "test-deny")

    def call(self, data=None, policy=None, capability="test.echo"):
        return self.registry.invoke(Invocation("test-principal", capability, data,
                                                policy or self.allow))

    def test_registered_adapter_invokes_after_policy_allow(self):
        result = self.call({"x": 1})
        self.assertTrue(result.ok)
        self.assertEqual(result.output, {"received": {"x": 1}})
        self.assertEqual(result.decision_id, "test-allow")

    def test_policy_denial_fails_closed(self):
        result = self.call({"x": 1}, self.deny)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "policy_denied")

    def test_policy_exception_fails_closed(self):
        result = self.call({"x": 1}, lambda _: (_ for _ in ()).throw(RuntimeError()))
        self.assertEqual(result.error_code, "policy_error")

    def test_unknown_capability_is_denied(self):
        self.assertEqual(self.call({}, capability="missing").error_code,
                         "capability_not_registered")

    def test_duplicate_adapter_id_rejected(self):
        with self.assertRaises(AdapterError):
            self.registry.register(Echo())

    def test_oversized_input_rejected(self):
        registry = AdapterRegistry(max_payload_bytes=8)
        registry.register(Echo())
        result = registry.invoke(Invocation("p", "test.echo", {"large": "payload"}, self.allow))
        self.assertEqual(result.error_code, "invalid_or_oversized_input")

    def test_non_json_input_rejected(self):
        result = self.call({"bad": object()})
        self.assertEqual(result.error_code, "invalid_or_oversized_input")

    def test_non_finite_json_number_rejected(self):
        result = self.call(float("nan"))
        self.assertEqual(result.error_code, "invalid_or_oversized_input")

    def test_oversized_output_rejected(self):
        class Large:
            adapter_id = "test.large"
            capabilities = frozenset({"test.large"})
            def invoke(self, input_data):
                return "x" * 100
        registry = AdapterRegistry(max_payload_bytes=10)
        registry.register(Large())
        result = registry.invoke(Invocation("p", "test.large", {}, self.allow))
        self.assertEqual(result.error_code, "invalid_or_oversized_output")

    def test_adapter_exception_is_contained(self):
        class Broken:
            adapter_id = "test.broken"
            capabilities = frozenset({"test.broken"})
            def invoke(self, input_data):
                raise RuntimeError("private detail")
        registry = AdapterRegistry()
        registry.register(Broken())
        result = registry.invoke(Invocation("p", "test.broken", {}, self.allow))
        self.assertEqual(result.error_code, "adapter_error")
        self.assertNotIn("private detail", result.error_message)

    def test_duplicate_capability_rejected(self):
        class Other:
            adapter_id = "test.other"
            capabilities = frozenset({"test.echo"})
            def invoke(self, input_data):
                return input_data
        with self.assertRaises(AdapterError):
            self.registry.register(Other())

    def test_registered_capabilities_are_snapshotted(self):
        class Mutable:
            adapter_id = "test.mutable"
            capabilities = {"test.mutable"}
            def invoke(self, input_data):
                return input_data
        registry = AdapterRegistry()
        adapter = Mutable()
        registry.register(adapter)
        adapter.capabilities.add("test.injected")
        self.assertEqual(registry.descriptors()[0]["capabilities"], ["test.mutable"])

    def test_descriptor_output_is_deterministic(self):
        self.assertEqual(self.registry.descriptors(),
                         [{"adapter_id": "test.echo", "capabilities": ["test.echo"]}])

if __name__ == "__main__":
    unittest.main()
