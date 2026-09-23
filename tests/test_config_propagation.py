import logging
import random
import time

import synpp

class StageA:
	def configure(self, context):
		context.config("a")

	def execute(self, context):
		pass

class StageB:
	def configure(self, context):
		context.config("b")

	def execute(self, context):
		pass

class StageShared:
	def configure(self, context):
		context.stage(StageA)

	def execute(self, context):
		pass

class StageLeft:
	def configure(self, context):
		context.stage(StageShared)

	def execute(self, context):
		pass

class StageRight:
	def configure(self, context):
		context.stage(StageShared)
		context.stage(StageB)

	def execute(self, context):
		pass

class StageJoin:
	def configure(self, context):
		context.stage(StageLeft)
		context.stage(StageRight)

	def execute(self, context):
		pass

def test_config_propagation(tmpdir):
	for k in range(20):
		result = synpp.run(
			[{ "descriptor": StageJoin }], 
			config = {"a": 1, "b": 2}, 
			working_directory = str(tmpdir),
			verbose = True)

		assert len(result["stale"]) == 1 or "tests.test_config_propagation.StageRight__8aacdb17187e6acf2b175d4aa08d7213" in result["stale"]
		assert "tests.test_config_propagation.StageJoin__8aacdb17187e6acf2b175d4aa08d7213" in result["stale"]
