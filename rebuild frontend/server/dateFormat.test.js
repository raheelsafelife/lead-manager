import test from "node:test";
import assert from "node:assert/strict";
import { calendarDateParts, formatCalendarDate } from "../src/utils/dateFormat.js";

test("DOB remains the same calendar day", () => {
  assert.equal(formatCalendarDate("1975-05-20", "en-US"), "5/20/1975");
});

test("calendar dates remain unchanged when returned with a timestamp suffix", () => {
  assert.equal(formatCalendarDate("1975-05-20T00:00:00.000Z", "en-US"), "5/20/1975");
});

test("calendar date parts do not pass through JavaScript timezone conversion", () => {
  assert.deepEqual(calendarDateParts("1975-05-20"), { year: 1975, month: 5, day: 20 });
});
