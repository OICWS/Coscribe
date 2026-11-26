import { useEffect, useId, useLayoutEffect, useRef } from "react";
import type { ConversationActivity } from "../../lib/transcriptGrouping";
import { CYCLE, DEPARTED, GATHER, eyeAt, poseAt, smooth, wave } from "./activityRobotMotion";

const DOTS = [19, 30, 41];

function animateRobot(svg: SVGSVGElement, currentActivity: () => ConversationActivity) {
  const [shadow, dots, head] = svg.querySelectorAll<SVGGraphicsElement>("[data-part]");
  const eyes = head.querySelectorAll("path");
  const circles = dots.querySelectorAll("circle");
  const root = document.documentElement;
  let frame = 0;
  let previous: number | undefined;
  let time = 0;
  let selectedCycle = -1;
  let gesture = currentActivity();

  function paint(now: number) {
    // This clock stays with the indicator when new tokens or tool events redraw the status row.
    if (previous !== undefined) time += Math.min((now - previous) / 1000, 0.1);
    previous = now;
    const cycle = Math.floor(time / CYCLE);
    const phase = time - cycle * CYCLE;
    if (phase >= GATHER && selectedCycle !== cycle) {
      selectedCycle = cycle;
      gesture = currentActivity();
      svg.dataset.gesture = gesture;
    }
    if (phase >= DEPARTED && svg.dataset.gesture) delete svg.dataset.gesture;

    const shape = smooth(GATHER, 0.92, phase) * (1 - smooth(2.94, DEPARTED, phase));
    const appear = smooth(0.07, 0.92, shape);
    circles.forEach((dot, index) => {
      const pulse = 0.5 + 0.5 * wave(time, 0.91, -index * 1.85);
      dot.setAttribute("cx", String(30 + (DOTS[index] - 30) * (1 - 0.95 * shape)));
      dot.setAttribute("r", String(2.85 + 1.02 * pulse + 1.3 * shape));
      dot.setAttribute("opacity", String((0.48 + 0.46 * pulse) * (1 - smooth(0.45, 0.94, shape))));
    });

    head.setAttribute("opacity", String(smooth(0.16, 0.68, shape)));
    if (appear > 0) {
      const pose = poseAt(gesture, phase, time);
      const [yaw, pitch] = pose;
      const arrived = Math.max(0, phase - 0.89);
      const settle = Math.sin(arrived * 17) * Math.exp(-8.5 * arrived);
      const lift = 2.7 * pitch - 2.8 * settle * appear;
      const drift = 2.15 * yaw;
      const size = 0.2 + 0.8 * appear + 0.018 * appear * wave(time, 2.63);
      head.setAttribute("transform", `translate(${30 + drift} ${30 + lift}) scale(${size * (1 + 0.09 * settle)} ${size * (1 - 0.11 * settle)})`);
      shadow.setAttribute("cx", String(30 + drift * 0.72));
      shadow.setAttribute("rx", String(19 + lift * 0.83));
      shadow.setAttribute("opacity", String((0.66 + 0.055 * lift) * appear));
      const revealEyes = smooth(0.74, 0.98, shape);
      eyes.forEach((eye, index) => {
        const { path, opacity } = eyeAt(index === 0 ? -1 : 1, pose);
        eye.setAttribute("d", path);
        eye.setAttribute("opacity", String(revealEyes * opacity));
      });
    } else {
      shadow.setAttribute("opacity", "0");
    }
    frame = requestAnimationFrame(paint);
  }

  function updatePlayback() {
    cancelAnimationFrame(frame);
    previous = undefined;
    if (root.dataset.motion === "reduced") {
      time = 0;
      selectedCycle = -1;
      delete svg.dataset.gesture;
      shadow.setAttribute("opacity", "0");
      head.setAttribute("opacity", "0");
      circles.forEach((dot, index) => {
        dot.setAttribute("cx", String(DOTS[index]));
        dot.setAttribute("r", "3.25");
        dot.setAttribute("opacity", "0.75");
      });
    } else if (!document.hidden) {
      frame = requestAnimationFrame(paint);
    }
  }

  // Appearance combines the saved app setting with the operating system preference.
  const appearance = new MutationObserver(updatePlayback);
  appearance.observe(root, { attributes: true, attributeFilter: ["data-motion"] });
  document.addEventListener("visibilitychange", updatePlayback);
  updatePlayback();
  return () => {
    appearance.disconnect();
    document.removeEventListener("visibilitychange", updatePlayback);
    cancelAnimationFrame(frame);
  };
}

export function ActivityRobot({ activity }: { activity: ConversationActivity }) {
  const id = useId();
  const graphic = useRef<SVGSVGElement>(null);
  const latest = useRef(activity);
  useLayoutEffect(() => {
    latest.current = activity;
  }, [activity]);

  useEffect(() => {
    const svg = graphic.current;
    if (svg) return animateRobot(svg, () => latest.current);
  }, []);

  return (
    <svg ref={graphic} aria-hidden="true" data-testid="activity-robot" viewBox="0 0 60 60"
      className="h-5 w-[22px] flex-none self-center text-[var(--muted)]">
      <defs>
        <radialGradient id={id + "-shell"} cx="31%" cy="24%" r="78%">
          <stop offset="0" stopColor="#b3c8e2" />
          <stop offset=".28" stopColor="#7a96bb" />
          <stop offset=".56" stopColor="#4d6e9a" />
          <stop offset=".79" stopColor="#2a4060" />
          <stop offset=".93" stopColor="#30486a" />
          <stop offset="1" stopColor="#192941" className="dark:[stop-color:#384f70]" />
        </radialGradient>
        <radialGradient id={id + "-glint"} cx="33%" cy="26%" r="46%">
          <stop stopColor="#edf6ff" stopOpacity=".52" />
          <stop offset=".42" stopColor="#d3e8ff" stopOpacity=".15" />
          <stop offset="1" stopColor="#d3e8ff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={id + "-reflected-light"} cx="79%" cy="83%" r="60%">
          <stop stopColor="#8cb9f2" stopOpacity=".32" />
          <stop offset=".45" stopColor="#77a8e8" stopOpacity=".11" />
          <stop offset="1" stopColor="#77a8e8" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={id + "-shadow"}>
          <stop stopColor="currentColor" stopOpacity=".46" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
        <clipPath id={id + "-face"}><circle r="19.7" /></clipPath>
      </defs>
      <ellipse data-part="shadow" cx="30" cy="51" rx="20" ry="4.2" fill={`url(#${id}-shadow)`} opacity="0" />
      <g data-part="dots" fill="currentColor">
        {DOTS.map((x) => <circle key={x} cx={x} cy={30} r="3.25" opacity=".75" />)}
      </g>
      <g data-part="head" opacity="0">
        <circle r="19.7" fill={`url(#${id}-shell)`} />
        <circle r="19.7" fill={`url(#${id}-reflected-light)`} />
        <circle r="19.7" fill={`url(#${id}-glint)`} />
        <circle r="19.4" fill="none" stroke="#26394f" strokeOpacity=".24" strokeWidth=".55" />
        <g clipPath={`url(#${id}-face)`} fill="#fffef7"><path /><path /></g>
      </g>
    </svg>
  );
}
