# -*- coding: utf-8 -*-
import unittest
from core.lua_obfuscator import LuaObfuscator

class TestLuaObfuscator(unittest.TestCase):
    def test_obfuscate_and_stealth(self):
        raw_code = "print('ROBLOX_TEST_EXECUTION')"
        obfuscated = LuaObfuscator.obfuscate_and_stealth(raw_code, stealth_padding_lines=100)
        
        self.assertTrue(obfuscated.startswith("--[[ \n"))
        self.assertIn("loadstring or load", obfuscated)
        self.assertNotIn("ROBLOX_TEST_EXECUTION", obfuscated)  # Raw string must be encrypted
        self.assertGreater(obfuscated.count("\n"), 100)

if __name__ == "__main__":
    unittest.main()
